import os
import logging
import threading
import time
from app.monitor_agent import MemoryMonitorAgent
from app.predictor_agent import MemoryPredictorAgent
from app.healer_agent import MemoryHealerAgent
from app.rag_pipeline import RagPipeline
from app.ingestion import LogIngestionSystem
from web_interface import app

# Export the app for Gunicorn to use
# The variable name must match the one in the Gunicorn command

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def ensure_directories():
    """Create necessary directories if they don't exist."""
    dirs = ["logs", "data", "data/vector_store", "data/monitor_cache", 
            "data/predictor_cache", "data/healer_cache"]
    
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def start_agents():
    """Initialize and start memory management agents."""
    try:
        # Create ingestion system
        ingestion = LogIngestionSystem()
        ingestion.start()
        
        # Create RAG pipeline
        rag = RagPipeline()
        
        # Initialize agents with the RAG pipeline
        monitor = MemoryMonitorAgent(rag)
        predictor = MemoryPredictorAgent(rag)
        healer = MemoryHealerAgent(rag)
        
        # Start agents in separate threads
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
    
    # Ensure all required directories exist
    ensure_directories()
    
    # Start memory agents
    agents = start_agents()
    
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Self-Healing Memory System")
        # Cleanup could be added here
        
if __name__ == "__main__":
    main()
