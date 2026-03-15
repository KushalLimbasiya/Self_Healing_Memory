"""
predictor_agent.py — Periodically produces memory forecasts using MemoryPredictor.
Saves results to EventStore for the dashboard and API.
"""
import logging
import threading
import time
from typing import Optional

from app.ml.predictor import MemoryPredictor

logger = logging.getLogger(__name__)

FORECAST_INTERVAL = 300   # produce a new forecast every 5 minutes


class PredictorAgent:
    """
    Runs in a background thread. Every FORECAST_INTERVAL seconds, calls
    MemoryPredictor.forecast() and saves the result to EventStore.
    """

    def __init__(self, event_store, predictor: MemoryPredictor):
        self._store = event_store
        self._predictor = predictor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_forecast: dict = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="PredictorAgent")
        self._thread.start()
        logger.info("PredictorAgent started (interval=%ds)", FORECAST_INTERVAL)

    def stop(self) -> None:
        self._running = False
        logger.info("PredictorAgent stopped")

    # ── Public API ─────────────────────────────────────────────────────────────

    def last_forecast(self) -> dict:
        return self._last_forecast

    def predict_now(self) -> dict:
        """Force an immediate forecast (used by API endpoints)."""
        return self._run_forecast()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        # Initial short delay to let MonitorAgent collect some samples first
        time.sleep(60)
        while self._running:
            try:
                self._run_forecast()
            except Exception as e:
                logger.error("PredictorAgent loop error: %s", e)
            time.sleep(FORECAST_INTERVAL)

    def _run_forecast(self) -> dict:
        forecast = self._predictor.forecast()
        self._last_forecast = forecast

        if forecast.get("predicted_1h") is not None:
            self._store.save_prediction(forecast)
            logger.info(
                "Forecast: 1h=%.1f%% | 6h=%.1f%% | trend=%s | method=%s | confidence=%.2f",
                forecast.get("predicted_1h", 0),
                forecast.get("predicted_6h", 0),
                forecast.get("trend", "?"),
                forecast.get("method", "?"),
                forecast.get("confidence", 0),
            )
        else:
            logger.debug("PredictorAgent: not enough samples yet (%d)", forecast.get("samples", 0))

        return forecast
