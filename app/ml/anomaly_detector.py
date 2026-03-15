"""
anomaly_detector.py — Isolation Forest based memory anomaly detection.
Falls back to Z-score until enough samples are collected.
"""
import logging
import threading
import numpy as np
from collections import deque
from typing import Dict

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_MODEL = 50
BUFFER_MAX = 500


class AnomalyDetector:
    """
    Detects abnormal memory usage using:
      - Z-score  (immediate, works from sample 1)
      - Isolation Forest (kicks in after MIN_SAMPLES_FOR_MODEL readings)
    Retrains the model every 100 new samples automatically.
    """

    def __init__(self, event_store=None):
        self._buffer: deque = deque(maxlen=BUFFER_MAX)
        self._model = None
        self._lock = threading.Lock()
        self._samples_since_retrain = 0
        self._retrain_every = 100
        self._store = event_store

        # Load persisted samples from DB so we don't restart cold
        if self._store:
            try:
                saved = self._store.load_ml_samples("anomaly", limit=BUFFER_MAX)
                for s in saved:
                    self._buffer.append(s)
                if saved:
                    logger.info("AnomalyDetector: loaded %d samples from DB", len(saved))
                    # Trigger immediate training if we have enough
                    if len(self._buffer) >= MIN_SAMPLES_FOR_MODEL:
                        threading.Thread(target=self._retrain, daemon=True).start()
            except Exception as e:
                logger.warning("AnomalyDetector: could not load samples from DB: %s", e)

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_sample(self, used_percent: float) -> None:
        """Add a new memory reading to the buffer."""
        with self._lock:
            self._buffer.append(used_percent)
            self._samples_since_retrain += 1

        # Persist to DB (so survives restarts)
        if self._store:
            try:
                self._store.save_ml_sample("anomaly", used_percent)
            except Exception:
                pass

        if (len(self._buffer) >= MIN_SAMPLES_FOR_MODEL
                and self._samples_since_retrain >= self._retrain_every):
            threading.Thread(target=self._retrain, daemon=True).start()

    def detect(self, stats: dict) -> Dict:
        """
        Analyse current stats for anomalies.
        Returns: { is_anomaly, score, method, description }
        """
        used = stats.get("used_percent", 0)

        with self._lock:
            buf = list(self._buffer)

        if self._model and len(buf) >= MIN_SAMPLES_FOR_MODEL:
            return self._isolation_forest_detect(used, buf)
        return self._zscore_detect(used, buf)

    def status(self) -> Dict:
        return {
            "samples_collected": len(self._buffer),
            "model_ready": self._model is not None,
            "method": "isolation_forest" if self._model else "zscore",
            "min_samples_needed": MIN_SAMPLES_FOR_MODEL,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _zscore_detect(self, used: float, buf: list) -> Dict:
        if len(buf) < 5:
            return {
                "is_anomaly": False, "score": 0.0,
                "method": "insufficient_data",
                "description": "Not enough samples yet",
            }
        arr = np.array(buf)
        mean, std = arr.mean(), arr.std()
        if std == 0:
            return {"is_anomaly": False, "score": 0.0, "method": "zscore",
                    "description": "Memory usage stable"}
        z = abs((used - mean) / std)
        is_anomaly = z > 2.5
        return {
            "is_anomaly": bool(is_anomaly),
            "score": round(float(z), 3),
            "method": "zscore",
            "description": f"Z-score {z:.2f} — {'ANOMALY' if is_anomaly else 'normal'}",
        }

    def _isolation_forest_detect(self, used: float, buf: list) -> Dict:
        try:
            X = np.array([[v] for v in buf])
            pred = self._model.predict([[used]])[0]   # 1=normal, -1=anomaly
            score = -self._model.score_samples([[used]])[0]  # higher = more anomalous
            is_anomaly = bool(pred == -1)
            return {
                "is_anomaly": is_anomaly,
                "score": round(float(score), 4),
                "method": "isolation_forest",
                "description": f"IF score {score:.3f} — {'ANOMALY' if is_anomaly else 'normal'}",
            }
        except Exception as e:
            logger.warning("IF detection failed, falling back to zscore: %s", e)
            return self._zscore_detect(used, buf)

    def _retrain(self) -> None:
        try:
            from sklearn.ensemble import IsolationForest
            with self._lock:
                data = list(self._buffer)
                self._samples_since_retrain = 0
            X = np.array([[v] for v in data])
            model = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
            model.fit(X)
            with self._lock:
                self._model = model
            logger.info("AnomalyDetector: Isolation Forest retrained on %d samples", len(data))
        except Exception as e:
            logger.error("AnomalyDetector retrain failed: %s", e)
