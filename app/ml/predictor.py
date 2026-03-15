"""
predictor.py — Holt-Winters exponential smoothing for memory forecasting.
Falls back to linear regression (numpy.polyfit) if statsmodels is unavailable.
"""
import logging
import threading
import numpy as np
from collections import deque
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BUFFER_MAX = 200
MIN_SAMPLES_FOR_HW = 24   # need at least 24 points for Holt-Winters to work well


class MemoryPredictor:
    """
    Forecasts future memory usage using Holt-Winters exponential smoothing.
    Outputs predicted_1h, predicted_6h, trend, confidence.
    """

    def __init__(self, poll_interval_seconds: int = 10, event_store=None):
        self._buffer: deque = deque(maxlen=BUFFER_MAX)
        self._timestamps: deque = deque(maxlen=BUFFER_MAX)
        self._lock = threading.Lock()
        self._poll_interval = poll_interval_seconds
        self._store = event_store

        # Load persisted samples from DB so predictions resume after restart
        if self._store:
            try:
                saved = self._store.load_ml_samples("predictor", limit=BUFFER_MAX)
                for s in saved:
                    self._buffer.append(s)
                    self._timestamps.append(datetime.now().isoformat())
                if saved:
                    logger.info("MemoryPredictor: loaded %d samples from DB", len(saved))
            except Exception as e:
                logger.warning("MemoryPredictor: could not load samples from DB: %s", e)

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_sample(self, used_percent: float, ts: Optional[str] = None) -> None:
        """Record a new memory % reading."""
        with self._lock:
            self._buffer.append(used_percent)
            self._timestamps.append(ts or datetime.now().isoformat())

        # Persist to DB
        if self._store:
            try:
                self._store.save_ml_sample("predictor", used_percent)
            except Exception:
                pass

    def forecast(self) -> Dict:
        """
        Produce a forecast dict:
          predicted_1h, predicted_6h, trend, confidence, method
        """
        with self._lock:
            data = list(self._buffer)

        n = len(data)
        if n < 5:
            return {
                "predicted_1h": None, "predicted_6h": None,
                "trend": "unknown", "confidence": 0.0,
                "method": "insufficient_data",
                "samples": n,
            }

        if n >= MIN_SAMPLES_FOR_HW:
            result = self._holt_winters_forecast(data)
        else:
            result = self._linear_forecast(data)

        result["samples"] = n
        return result

    def status(self) -> Dict:
        return {
            "samples_in_buffer": len(self._buffer),
            "min_for_holt_winters": MIN_SAMPLES_FOR_HW,
            "ready": len(self._buffer) >= MIN_SAMPLES_FOR_HW,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _steps_for(self, hours: float) -> int:
        """Convert hours to number of prediction steps given poll interval."""
        return max(1, int((hours * 3600) / self._poll_interval))

    def _trend_label(self, data: list) -> str:
        if len(data) < 3:
            return "stable"
        recent = data[-6:]      # last 6 readings
        slope = np.polyfit(range(len(recent)), recent, 1)[0]
        if slope > 0.5:
            return "rising"
        if slope < -0.5:
            return "falling"
        return "stable"

    def _clamp(self, val: float) -> float:
        return round(float(max(0.0, min(100.0, val))), 2)

    def _holt_winters_forecast(self, data: list) -> Dict:
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            import warnings
            steps_1h = self._steps_for(1)
            steps_6h = self._steps_for(6)

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = ExponentialSmoothing(
                    data,
                    trend="add",
                    damped_trend=True,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=True, disp=False)

            forecast_6h = fit.forecast(steps_6h)
            pred_1h = self._clamp(float(forecast_6h[min(steps_1h - 1, len(forecast_6h) - 1)]))
            pred_6h = self._clamp(float(forecast_6h[-1]))

            # Confidence: lower if variance is high
            residuals = np.array(fit.resid)
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            confidence = round(max(0.0, min(1.0, 1.0 - (rmse / 50.0))), 2)

            return {
                "predicted_1h": pred_1h,
                "predicted_6h": pred_6h,
                "trend": self._trend_label(data),
                "confidence": confidence,
                "method": "holt_winters",
            }
        except Exception as e:
            logger.warning("Holt-Winters failed (%s), using linear fallback", e)
            return self._linear_forecast(data)

    def _linear_forecast(self, data: list) -> Dict:
        x = np.arange(len(data))
        slope, intercept = np.polyfit(x, data, 1)

        steps_1h = self._steps_for(1)
        steps_6h = self._steps_for(6)
        n = len(data)

        pred_1h = self._clamp(intercept + slope * (n + steps_1h))
        pred_6h = self._clamp(intercept + slope * (n + steps_6h))

        r_squared = self._r_squared(data, slope, intercept)
        confidence = round(float(max(0.0, min(1.0, r_squared))), 2)

        return {
            "predicted_1h": pred_1h,
            "predicted_6h": pred_6h,
            "trend": self._trend_label(data),
            "confidence": confidence,
            "method": "linear_regression",
        }

    @staticmethod
    def _r_squared(data: list, slope: float, intercept: float) -> float:
        x = np.arange(len(data))
        y = np.array(data)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        return 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
