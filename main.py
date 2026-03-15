"""
main.py — Entry point for the Self-Healing Memory system.

Creates all components, injects dependencies, starts agent threads,
then runs Flask in the main thread.
"""
import logging
import os

# Ensure required directories exist before anything else
os.makedirs("data",      exist_ok=True)
os.makedirs("logs",      exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/css", exist_ok=True)

from app             import create_app
from app             import event_store
from app.ml.anomaly_detector import AnomalyDetector
from app.ml.predictor        import MemoryPredictor
from app.ml.healer_brain     import HealerBrain
from app.monitor_agent       import MonitorAgent
from app.predictor_agent     import PredictorAgent
from app.healer_agent        import HealerAgent

logger = logging.getLogger(__name__)


def build_system():
    """Instantiate and wire all components. Returns (app, agents_dict)."""

    # 1. DB
    event_store.init_db()

    # 2. ML modules (shared across agents — single instances)
    detector  = AnomalyDetector(event_store=event_store)
    predictor = MemoryPredictor(poll_interval_seconds=10, event_store=event_store)
    brain     = HealerBrain(event_store)

    # 3. Agents (dependency-injected)
    monitor   = MonitorAgent(event_store, detector, predictor)
    pred_agent = PredictorAgent(event_store, predictor)
    healer    = HealerAgent(event_store, brain)

    agents = {
        "monitor":   monitor,
        "predictor": pred_agent,
        "healer":    healer,
        "detector":  detector,
        "brain":     brain,
        "ml_predictor": predictor,
    }

    # 4. Flask app
    flask_app = create_app()

    # 5. Register routes (import here to avoid circular imports)
    from web_interface import register_routes
    register_routes(flask_app, agents)

    return flask_app, agents


if __name__ == "__main__":
    app, agents = build_system()

    # Start agent background threads
    agents["monitor"].start()
    agents["predictor"].start()
    agents["healer"].start()
    logger.info("All agents started")

    # Flask runs in main thread
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting Flask on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
