import os
import logging
import threading
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/system.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Create necessary directories if they don't exist."""
    dirs = ["logs", "data", "data/vector_store", "data/monitor_cache", 
            "data/predictor_cache", "data/healer_cache"]
    
    for directory in dirs:
        win_dir = directory.replace('/', '\\')
        if not os.path.exists(win_dir):
            os.makedirs(win_dir)
            logger.info(f"Created directory: {win_dir}")

ensure_directories()
# Set environment variable to disable SQLAlchemy
os.environ['DISABLE_DATABASE'] = 'true'
logger.info("Database functionality disabled")

from web_interface import app as application
import models

from app.monitor_agent import MemoryMonitorAgent
from app.predictor_agent import MemoryPredictorAgent
from app.healer_agent import MemoryHealerAgent
from app.rag_pipeline import RagPipeline
from app.ingestion import LogIngestionSystem

app = application

def start_agents():
    """Initialize and start memory management agents."""
    try:
        ingestion = LogIngestionSystem()
        ingestion.start()
        
        rag = RagPipeline()
        
        monitor = MemoryMonitorAgent(rag)
        predictor = MemoryPredictorAgent(rag)
        healer = MemoryHealerAgent(rag)
        
        monitor.start_monitoring()
        predictor.start_prediction_service()
        healer.start_healing_service()
        
        logger.info("All agents started successfully")
        
        return monitor, predictor, healer, ingestion
    except Exception as e:
        logger.error(f"Failed to start agents: {str(e)}")
        raise

def main():
    """Main entry point for the self-healing memory system."""
    logger.info("Starting Self-Healing Memory System")
    
    agents = start_agents()
    
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Self-Healing Memory System")
        
if __name__ == "__main__":
    main()
