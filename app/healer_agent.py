"""
healer_agent.py — Self-healing memory agent driven by HealerBrain.

When memory usage crosses thresholds, HealerBrain recommends the most
historically effective healing actions. Results are fed back to HealerBrain
to improve future decisions (feedback loop).
"""
import gc
import logging
import threading
import time
from datetime import datetime
from typing import Optional

from app.memory_core import get_memory_stats, release_memory_cache

logger = logging.getLogger(__name__)

HEAL_CHECK_INTERVAL = 60     # check every 60 seconds
HEAL_THRESHOLD      = 75.0   # trigger healing above this %
COOLDOWN_SECONDS    = 120    # minimum seconds between healing actions


class HealerAgent:
    """
    Monitors memory and triggers healing actions when usage is high.
    Uses HealerBrain to pick the best action based on historical outcomes.
    Records results back to HealerBrain (self-learning feedback loop).
    """

    def __init__(self, event_store, healer_brain):
        self._store = event_store
        self._brain = healer_brain
        self._running = False
        self._paused  = False
        self._thread: Optional[threading.Thread] = None
        self._last_heal_time: float = 0.0
        self._last_result: dict = {}

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="HealerAgent")
        self._thread.start()
        logger.info("HealerAgent started (threshold=%.0f%%, interval=%ds)",
                    HEAL_THRESHOLD, HEAL_CHECK_INTERVAL)

    def stop(self) -> None:
        self._running = False
        logger.info("HealerAgent stopped")

    def pause(self) -> None:
        self._paused = True
        logger.info("HealerAgent paused (auto-heal OFF)")

    def resume(self) -> None:
        self._paused = False
        logger.info("HealerAgent resumed (auto-heal ON)")

    def is_paused(self) -> bool:
        return self._paused

    # ── Public API ─────────────────────────────────────────────────────────────

    def last_result(self) -> dict:
        return self._last_result

    def heal_now(self, execute: bool = False) -> dict:
        """
        Generate a healing plan and optionally execute it immediately.
        Used by the API endpoint.
        """
        stats = get_memory_stats()
        severity = self._severity(stats["used_percent"])
        plan = self._generate_plan(stats, severity)
        if execute:
            return self._execute_plan(stats, plan)
        return {"plan": plan, "stats": stats, "executed": False}

    # ── Internal ───────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                if self._paused:
                    time.sleep(HEAL_CHECK_INTERVAL)
                    continue
                stats = get_memory_stats()
                used = stats.get("used_percent", 0)

                if used >= HEAL_THRESHOLD:
                    now = time.time()
                    if now - self._last_heal_time >= COOLDOWN_SECONDS:
                        severity = self._severity(used)
                        plan = self._generate_plan(stats, severity)
                        self._execute_plan(stats, plan)
                        self._last_heal_time = now
                    else:
                        remaining = int(COOLDOWN_SECONDS - (time.time() - self._last_heal_time))
                        logger.debug("HealerAgent: cooldown active (%ds remaining)", remaining)
            except Exception as e:
                logger.error("HealerAgent loop error: %s", e)
            time.sleep(HEAL_CHECK_INTERVAL)

    def _generate_plan(self, stats: dict, severity: str) -> dict:
        recommendations = self._brain.recommend(severity)
        return {
            "severity": severity,
            "used_percent": stats.get("used_percent", 0),
            "recommended_actions": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    def _execute_plan(self, stats_before: dict, plan: dict) -> dict:
        used_before = stats_before.get("used_percent", 0)
        results = []

        for rec in plan["recommended_actions"]:
            action = rec["action"]
            success, freed_bytes = self._run_action(action)
            results.append({
                "action":  action,
                "success": success,
                "freed_bytes": freed_bytes,
            })

        stats_after = get_memory_stats()
        used_after = stats_after.get("used_percent", 0)
        freed_percent = max(0.0, used_before - used_after)

        validation = {
            "used_before": used_before,
            "used_after":  used_after,
            "freed_percent": round(freed_percent, 2),
            "effective": freed_percent > 1.0,
        }

        # Feedback loop: update HealerBrain scores
        for rec in plan["recommended_actions"]:
            share = freed_percent / max(len(plan["recommended_actions"]), 1)
            self._brain.update_score(rec["action"], share)

        self._store.save_healing_event(stats_before, plan, {"actions": results}, validation)

        self._last_result = {
            "plan": plan,
            "results": results,
            "validation": validation,
            "executed": True,
        }

        logger.info(
            "Healing complete: %.1f%% -> %.1f%% (freed %.2f%%)",
            used_before, used_after, freed_percent
        )
        return self._last_result

    # ── Healing Actions ────────────────────────────────────────────────────────

    def _run_action(self, action: str) -> tuple:
        """Execute a single healing action. Returns (success, freed_bytes)."""
        try:
            if action == "gc_collect":
                return self._action_gc()
            if action == "clear_cache":
                return self._action_clear_cache()
            if action == "log_alert":
                return self._action_log_alert()
            if action == "reduce_interval":
                return self._action_reduce_interval()
            logger.warning("Unknown action: %s", action)
            return False, 0
        except Exception as e:
            logger.error("Action '%s' failed: %s", action, e)
            return False, 0

    @staticmethod
    def _action_gc() -> tuple:
        stats_before = get_memory_stats()
        collected = gc.collect()
        stats_after = get_memory_stats()
        freed = max(0, stats_before["used"] - stats_after["used"])
        logger.info("gc_collect: freed %d objects, ~%d bytes", collected, freed)
        return True, freed

    @staticmethod
    def _action_clear_cache() -> tuple:
        stats_before = get_memory_stats()
        success = release_memory_cache()
        stats_after = get_memory_stats()
        freed = max(0, stats_before["used"] - stats_after["used"])
        logger.info("clear_cache: freed ~%d bytes", freed)
        return success, freed

    @staticmethod
    def _action_log_alert() -> tuple:
        logger.warning("[!] MEMORY ALERT: High memory usage detected - manual review recommended.")
        return True, 0

    @staticmethod
    def _action_reduce_interval() -> tuple:
        # Signal only — MonitorAgent would need to read a shared flag to act on this
        logger.info("reduce_interval: alert emitted (manual intervention may be needed)")
        return True, 0

    @staticmethod
    def _severity(used_percent: float) -> str:
        if used_percent >= 95:
            return "critical"
        if used_percent >= 85:
            return "high"
        if used_percent >= 75:
            return "moderate"
        return "low"
