"""
monitor_agent.py — Continuously monitors OS memory and detects anomalies.
Uses AnomalyDetector (Isolation Forest / Z-score) for smart anomaly detection.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional

from app.memory_core import get_memory_stats
from app.ml.anomaly_detector import AnomalyDetector
from app.ml.predictor import MemoryPredictor

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10   # seconds between readings (10s = 24 samples in 4min instead of 12min)


class MonitorAgent:
    """
    Runs in a background thread, polls memory stats every POLL_INTERVAL seconds,
    feeds data into the AnomalyDetector and MemoryPredictor, and persists events.
    """

    def __init__(self,
                 event_store,
                 anomaly_detector: AnomalyDetector,
                 predictor: MemoryPredictor):
        self._store = event_store
        self._detector = anomaly_detector
        self._predictor = predictor
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_stats: dict = {}
        self._last_analysis: dict = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="MonitorAgent")
        self._thread.start()
        logger.info("MonitorAgent started (interval=%ds)", POLL_INTERVAL)

    def stop(self) -> None:
        self._running = False
        logger.info("MonitorAgent stopped")

    # ── Public API (used by web_interface.py) ──────────────────────────────────

    def current_stats(self) -> dict:
        return self._last_stats

    def last_analysis(self) -> dict:
        return self._last_analysis

    def analyze_now(self) -> dict:
        """Force an immediate analysis of current memory state."""
        stats = get_memory_stats()
        return self._analyze(stats)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                stats = get_memory_stats()
                self._last_stats = stats
                analysis = self._analyze(stats)
                self._last_analysis = analysis
                self._store.save_memory_event(stats, analysis)
            except Exception as e:
                logger.error("MonitorAgent loop error: %s", e)
            time.sleep(POLL_INTERVAL)

    def _analyze(self, stats: dict) -> dict:
        used = stats.get("used_percent", 0)

        # Feed into ML modules
        self._detector.add_sample(used)
        self._predictor.add_sample(used)

        # Anomaly detection
        anomaly = self._detector.detect(stats)

        # Severity classification
        severity = self._classify_severity(used, anomaly["is_anomaly"])

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "used_percent": used,
            "severity": severity,
            "anomaly": anomaly,
            "status": self._status_message(used, severity),
        }

        if anomaly["is_anomaly"]:
            logger.warning(
                "ANOMALY detected | usage=%.1f%% | severity=%s | score=%.3f",
                used, severity, anomaly["score"]
            )

        return analysis

    @staticmethod
    def _classify_severity(used_percent: float, is_anomaly: bool) -> str:
        if used_percent >= 95 or (is_anomaly and used_percent >= 85):
            return "critical"
        if used_percent >= 85 or (is_anomaly and used_percent >= 70):
            return "high"
        if used_percent >= 70:
            return "moderate"
        return "low"

    @staticmethod
    def _status_message(used: float, severity: str) -> str:
        return {
            "critical": f"⛔ Critical — {used:.1f}% memory used. Immediate action required.",
            "high":     f"⚠️  High — {used:.1f}% memory used. Healing recommended.",
            "moderate": f"🟡 Moderate — {used:.1f}% memory used. Monitoring closely.",
            "low":      f"✅ Normal — {used:.1f}% memory used.",
        }.get(severity, "Unknown")
