import os
import time
import logging
import threading
import json
import subprocess
from datetime import datetime

from .memory_core import get_memory_stats

logger = logging.getLogger(__name__)

class LogIngestionSystem:
    """
    System for continuous ingestion of memory statistics into log files.
    """
    
    def __init__(self, interval=30):
        """
        Initialize the Log Ingestion System.
        
        Args:
            interval: Logging interval in seconds (default: 30)
        """
        self.interval = interval
        self.running = False
        self.ingestion_thread = None
        
        if not os.path.exists("data"):
            os.makedirs("data")
            
        logger.info("Log Ingestion System initialized")
        
    def start(self):
        """Start ingesting memory statistics in a separate thread."""
        if self.running:
            logger.warning("Ingestion is already running")
            return
            
        self.running = True
        
        self.ingestion_thread = threading.Thread(target=self._ingestion_loop)
        self.ingestion_thread.daemon = True
        self.ingestion_thread.start()
        
        logger.info(f"Memory statistics ingestion started with interval of {self.interval} seconds")
        
    def stop(self):
        """Stop the ingestion thread."""
        self.running = False
        if self.ingestion_thread:
            self.ingestion_thread.join(timeout=5.0)
        logger.info("Memory statistics ingestion stopped")
        
    def _ingestion_loop(self):
        """Main ingestion loop that runs in a separate thread."""
        while self.running:
            try:
                memory_stats = get_memory_stats()
                
                memory_event = {
                    "timestamp": datetime.now().isoformat(),
                    "stats": memory_stats
                }
                self._write_memory_event(memory_event)
                
                time.sleep(self.interval)
                    
            except Exception as e:
                logger.error(f"Error in ingestion loop: {str(e)}")
                time.sleep(self.interval)
    
    def _write_memory_event(self, memory_event):
        """
        Write memory event to a log file.
        
        Args:
            memory_event: Memory event dictionary to write
        """
        try:
            with open("data/memory_events.jsonl", "a") as f:
                f.write(json.dumps(memory_event) + "\n")
        except Exception as e:
            logger.error(f"Error writing memory event: {str(e)}")
