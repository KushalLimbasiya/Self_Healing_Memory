"""
web_interface.py — Flask routes for the Self-Healing Memory system.

All agents are passed in via register_routes() — no duplicate instances,
no ORM, no LLM calls. Pure REST API + dashboard template.
"""
import logging
from flask import Flask, jsonify, render_template, request

from app import event_store as es
from app.memory_core import get_top_processes, full_system_optimize, release_memory_cache

logger = logging.getLogger(__name__)


def register_routes(app: Flask, agents: dict) -> None:
    """Bind all routes onto the Flask app with access to shared agent instances."""

    monitor    = agents["monitor"]
    pred_agent = agents["predictor"]
    healer     = agents["healer"]
    detector   = agents["detector"]
    brain      = agents["brain"]
    predictor  = agents["ml_predictor"]

    # ── Dashboard ──────────────────────────────────────────────────────────────

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html")

    # ── Memory ─────────────────────────────────────────────────────────────────

    @app.route("/api/memory/current")
    def api_memory_current():
        stats    = monitor.current_stats()
        analysis = monitor.last_analysis()
        return jsonify({"success": True, "stats": stats, "analysis": analysis})

    @app.route("/api/memory/processes")
    def api_memory_processes():
        limit = request.args.get("limit", 8, type=int)
        return jsonify({"success": True, "processes": get_top_processes(limit)})

    @app.route("/api/memory/analyze", methods=["POST"])
    def api_memory_analyze():
        analysis = monitor.analyze_now()
        return jsonify({"success": True, "analysis": analysis})

    @app.route("/api/memory/optimize", methods=["POST"])
    def api_memory_optimize():
        """Trigger deep system-wide memory optimization (CleanMem / Wise MO technique)."""
        result = full_system_optimize()
        return jsonify({"success": True, **result})

    @app.route("/api/memory/quick_heal", methods=["POST"])
    def api_memory_quick_heal():
        """Trigger light optimization (GC + local working set trim)."""
        success = release_memory_cache()
        # Return a similar structure so UI doesn't break
        return jsonify({
            "success": success, 
            "freed_mb": 0, # harder to measure local-only freed accurately here without overhead
            "message": "Local cache released" if success else "Failed"
        })

    @app.route("/api/memory/anomalies")
    def api_memory_anomalies():
        limit = request.args.get("limit", 15, type=int)
        anomalies = es.get_recent_anomalies(limit=limit)
        return jsonify({"success": True, "anomalies": anomalies})

    @app.route("/api/memory/history")
    def api_memory_history():
        limit   = request.args.get("limit", 100, type=int)
        history = es.get_memory_history_series(limit=limit)
        return jsonify({"success": True, "history": history, "count": len(history)})

    # ── Prediction ─────────────────────────────────────────────────────────────

    @app.route("/api/memory/predict", methods=["POST"])
    def api_memory_predict():
        forecast = pred_agent.predict_now()
        return jsonify({"success": True, "forecast": forecast})

    @app.route("/api/memory/predict/latest")
    def api_memory_predict_latest():
        forecast = es.get_latest_prediction()
        return jsonify({"success": True, "forecast": forecast})

    # ── Healing ────────────────────────────────────────────────────────────────

    @app.route("/api/memory/heal", methods=["POST"])
    def api_memory_heal():
        body    = request.get_json(silent=True) or {}
        execute = body.get("execute", False)
        result  = healer.heal_now(execute=execute)
        return jsonify({"success": True, **result})

    @app.route("/api/heal/manual", methods=["POST"])
    def api_heal_manual():
        """Immediately trigger a healing cycle (manual / click-based, execute=True)."""
        try:
            result = healer.heal_now(execute=True)
            return jsonify({"success": True, "manual": True, **result})
        except Exception as e:
            logger.error("Manual heal error: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/heal/toggle", methods=["POST"])
    def api_heal_toggle():
        """Pause or resume the auto-healer."""
        if healer.is_paused():
            healer.resume()
            return jsonify({"success": True, "paused": False, "message": "Auto-healer resumed"})
        else:
            healer.pause()
            return jsonify({"success": True, "paused": True, "message": "Auto-healer paused"})

    @app.route("/api/heal/status")
    def api_heal_status():
        """Return whether auto-healer is currently paused."""
        return jsonify({"success": True, "paused": healer.is_paused()})

    # ── Logs ───────────────────────────────────────────────────────────────────

    @app.route("/api/logs/memory")
    def api_logs_memory():
        limit  = request.args.get("limit", 50, type=int)
        events = es.get_recent_memory_events(limit=limit)
        return jsonify({"success": True, "events": events, "count": len(events)})

    @app.route("/api/logs/healing")
    def api_logs_healing():
        limit  = request.args.get("limit", 20, type=int)
        events = es.get_recent_healing_events(limit=limit)
        return jsonify({"success": True, "events": events, "count": len(events)})

    @app.route("/api/logs/predictions")
    def api_logs_predictions():
        limit   = request.args.get("limit", 20, type=int)
        preds = es.get_recent_predictions(limit=limit)
        return jsonify({"success": True, "predictions": preds, "count": len(preds)})

    # ── ML Status ──────────────────────────────────────────────────────────────

    @app.route("/api/ml/status")
    def api_ml_status():
        return jsonify({
            "success": True,
            "anomaly_detector": detector.status(),
            "predictor":        predictor.status(),
            "healer_scoreboard": brain.scoreboard(),
        })

    # ── Health check ───────────────────────────────────────────────────────────

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok", "service": "self-healing-memory"})
