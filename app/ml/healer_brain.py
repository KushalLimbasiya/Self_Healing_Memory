"""
healer_brain.py — Self-learning feedback loop for memory healing decisions.

Tracks how much memory each action historically freed and scores actions
so the healer picks the most effective option over time.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Default starting scores (0.0–1.0 scale)
DEFAULT_ACTIONS = {
    "gc_collect":    0.6,   # Python GC — always safe, moderate effect
    "clear_cache":   0.7,   # OS cache release — usually effective
    "log_alert":     0.3,   # Logging alert only — no direct memory impact
    "reduce_interval": 0.4, # Increase monitoring frequency temporarily — no direct memory impact
}

# Actions that don't directly free memory — exclude from score updates
_NON_MEMORY_ACTIONS = {"log_alert", "reduce_interval"}


class HealerBrain:
    """
    Learns which healing actions are most effective by tracking outcomes.

    Works with event_store to persist scores across restarts.
    Falls back to DEFAULT_ACTIONS if no history yet.
    """

    def __init__(self, event_store_module=None):
        """
        Args:
            event_store_module: the app.event_store module (injected to avoid circular imports).
        """
        self._store = event_store_module
        self._scores: Dict[str, float] = {}
        self._load_scores()

    # ── Public API ─────────────────────────────────────────────────────────────

    def recommend(self, severity: str = "moderate") -> List[Dict]:
        """
        Return a ranked list of recommended healing actions.
        Higher-scoring actions come first.

        Args:
            severity: "low" | "moderate" | "high" | "critical"

        Returns:
            List of { action, score, description, priority }
        """
        actions = self._filter_by_severity(severity)
        ranked = sorted(actions, key=lambda a: self._scores.get(a, 0.5), reverse=True)
        return [
            {
                "action":      act,
                "score":       round(self._scores.get(act, 0.5), 3),
                "description": self._describe(act),
                "priority":    self._priority(act, severity),
            }
            for act in ranked
        ]

    def update_score(self, action: str, freed_percent: float) -> None:
        """
        Update the score for an action based on how effective it was.
        Non-memory actions (log_alert, reduce_interval) are skipped —
        they can never free RAM so penalizing them with 0% is misleading.
        """
        if action in _NON_MEMORY_ACTIONS:
            return  # These actions don't touch physical memory, don't score them

        old = self._scores.get(action, 0.5)
        # Exponential moving average — recent results weighted 20%
        new = old * 0.8 + (freed_percent / 100.0) * 0.2
        self._scores[action] = round(new, 4)
        logger.info("HealerBrain: '%s' score %.3f -> %.3f (freed %.1f%%)",
                    action, old, new, freed_percent)

        if self._store:
            try:
                self._store.update_action_score(action, freed_percent)
            except Exception as e:
                logger.warning("HealerBrain: could not persist score: %s", e)

    def scoreboard(self) -> List[Dict]:
        """Return all action scores sorted by score descending (for the ML Status page)."""
        if self._store:
            try:
                db_scores = self._store.get_action_scores()
                return sorted(
                    [
                        {
                            "action": k,
                            "score": round(v["score"], 3),
                            "times_used": v["times_used"],
                            "avg_freed": round(v["avg_freed"], 1),
                        }
                        for k, v in db_scores.items()
                    ],
                    key=lambda x: x["score"],
                    reverse=True,
                )
            except Exception as e:
                logger.warning("HealerBrain: scoreboard DB read failed: %s", e)

        return sorted(
            [{"action": k, "score": round(v, 3), "times_used": 0, "avg_freed": 0.0}
             for k, v in self._scores.items()],
            key=lambda x: x["score"],
            reverse=True,
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    def _load_scores(self) -> None:
        """Load scores from DB if available, otherwise use defaults."""
        loaded = {}
        if self._store:
            try:
                db = self._store.get_action_scores()
                loaded = {k: v["score"] for k, v in db.items()}
            except Exception as e:
                logger.warning("HealerBrain: could not load scores from DB: %s", e)

        # Merge defaults with any DB scores (DB wins)
        self._scores = {**DEFAULT_ACTIONS, **loaded}
        logger.info("HealerBrain initialised with scores: %s", self._scores)

    def _filter_by_severity(self, severity: str) -> List[str]:
        """Return appropriate action set for the given severity level."""
        if severity == "low":
            return ["log_alert", "reduce_interval"]
        if severity == "moderate":
            return ["gc_collect", "log_alert", "reduce_interval"]
        if severity == "high":
            return ["gc_collect", "clear_cache", "log_alert"]
        # critical
        return list(DEFAULT_ACTIONS.keys())

    @staticmethod
    def _describe(action: str) -> str:
        return {
            "gc_collect":      "Run Python garbage collector to free unreferenced objects",
            "clear_cache":     "Request OS to release memory page cache",
            "log_alert":       "Emit a high-severity alert to system log",
            "reduce_interval": "Temporarily increase monitoring poll frequency",
        }.get(action, action)

    @staticmethod
    def _priority(action: str, severity: str) -> str:
        if severity == "critical":
            return "high"
        if severity == "high" and action in ("gc_collect", "clear_cache"):
            return "high"
        return "medium"
