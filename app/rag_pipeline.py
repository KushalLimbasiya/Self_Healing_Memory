import os
import json
import logging
from datetime import datetime, timedelta
import threading
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RagPipeline:
    """
    Simplified Retrieval-Augmented Generation pipeline for context-aware memory management decisions.
    This implementation doesn't require ChromaDB or sentence-transformers.
    """
    
    def __init__(self):
        """Initialize the simplified RAG pipeline."""
        self.db_dir = "data"
        os.makedirs(self.db_dir, exist_ok=True)
        
        # In-memory storage for events (simplified version)
        self.memory_events = []
        self.predictions = []
        self.healing_events = []
        
        # Start ingestion thread
        self.running = True
        self.ingestion_thread = threading.Thread(target=self._background_ingestion)
        self.ingestion_thread.daemon = True
        self.ingestion_thread.start()
        
        logger.info("Simplified RAG Pipeline initialized")
    
    def _background_ingestion(self):
        """Background thread for ingesting log files into memory."""
        while self.running:
            try:
                self._ingest_memory_events_from_file()
                self._ingest_predictions_from_file()
                self._ingest_healing_events_from_file()
                
                # Sleep before next ingestion cycle
                time.sleep(60)  # Check for new log entries every minute
            except Exception as e:
                logger.error(f"Error in background ingestion: {str(e)}")
                time.sleep(60)
    
    def _ingest_memory_events_from_file(self):
        """Ingest memory events from log file into memory."""
        try:
            if not os.path.exists("data/memory_events.jsonl"):
                return
            
            # Read all lines from the file
            with open("data/memory_events.jsonl", "r") as f:
                lines = f.readlines()
            
            # Clear current events and reload (simple approach)
            self.memory_events = []
            
            # Load all events (limit to last 100 for performance)
            for line in lines[-100:]:
                try:
                    event = json.loads(line.strip())
                    self.memory_events.append(event)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in memory events file")
            
            logger.info(f"Loaded {len(self.memory_events)} memory events")
        except Exception as e:
            logger.error(f"Error ingesting memory events: {str(e)}")
    
    def _ingest_predictions_from_file(self):
        """Ingest predictions from log file into memory."""
        try:
            if not os.path.exists("data/memory_predictions.jsonl"):
                return
            
            # Read all lines from the file
            with open("data/memory_predictions.jsonl", "r") as f:
                lines = f.readlines()
            
            # Clear current predictions and reload
            self.predictions = []
            
            # Load all predictions (limit to last 100 for performance)
            for line in lines[-100:]:
                try:
                    prediction = json.loads(line.strip())
                    self.predictions.append(prediction)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in predictions file")
            
            logger.info(f"Loaded {len(self.predictions)} predictions")
        except Exception as e:
            logger.error(f"Error ingesting predictions: {str(e)}")
    
    def _ingest_healing_events_from_file(self):
        """Ingest healing events from log file into memory."""
        try:
            if not os.path.exists("data/healing_events.jsonl"):
                return
            
            # Read all lines from the file
            with open("data/healing_events.jsonl", "r") as f:
                lines = f.readlines()
            
            # Clear current healing events and reload
            self.healing_events = []
            
            # Load all healing events (limit to last 100 for performance)
            for line in lines[-100:]:
                try:
                    event = json.loads(line.strip())
                    self.healing_events.append(event)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in healing events file")
            
            logger.info(f"Loaded {len(self.healing_events)} healing events")
        except Exception as e:
            logger.error(f"Error ingesting healing events: {str(e)}")
    
    def add_memory_event(self, memory_stats, analysis):
        """
        Add a memory event to the log file.
        
        Args:
            memory_stats: Memory statistics
            analysis: Analysis results
        """
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "stats": memory_stats,
                "analysis": analysis
            }
            
            # Append to the memory events list
            self.memory_events.append(event)
            
            # Write to log file
            with open("data/memory_events.jsonl", "a") as f:
                f.write(json.dumps(event) + "\n")
            
            logger.debug("Memory event added")
        except Exception as e:
            logger.error(f"Error adding memory event: {str(e)}")
    
    def add_prediction(self, prediction):
        """
        Add a prediction to the log file.
        
        Args:
            prediction: Prediction dictionary
        """
        try:
            # Append to the predictions list
            self.predictions.append(prediction)
            
            # Write to log file
            with open("data/memory_predictions.jsonl", "a") as f:
                f.write(json.dumps(prediction) + "\n")
            
            logger.debug("Prediction added")
        except Exception as e:
            logger.error(f"Error adding prediction: {str(e)}")
    
    def add_healing_event(self, memory_stats, healing_plan, results, validation):
        """
        Add a healing event to the log file.
        
        Args:
            memory_stats: Memory statistics before healing
            healing_plan: Healing plan that was executed
            results: Results of the executed actions
            validation: Validation of healing effectiveness
        """
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "memory_stats": memory_stats,
                "healing_plan": healing_plan,
                "results": results,
                "validation": validation
            }
            
            # Append to the healing events list
            self.healing_events.append(event)
            
            # Write to log file
            with open("data/healing_events.jsonl", "a") as f:
                f.write(json.dumps(event) + "\n")
            
            logger.debug("Healing event added")
        except Exception as e:
            logger.error(f"Error adding healing event: {str(e)}")
    
    def get_relevant_memory_events(self, memory_stats, limit=5, time_window=3600):
        """
        Get relevant memory events based on current memory statistics.
        
        Args:
            memory_stats: Current memory statistics
            limit: Maximum number of events to return
            time_window: Time window in seconds
            
        Returns:
            List of relevant memory events
        """
        try:
            # Simple approach: get the most recent events
            events = sorted(self.memory_events, key=lambda e: e.get("timestamp", ""), reverse=True)
            return events[:limit]
        except Exception as e:
            logger.error(f"Error getting relevant memory events: {str(e)}")
            return []
    
    def get_recent_predictions(self, limit=5):
        """
        Get recent predictions.
        
        Args:
            limit: Maximum number of predictions to return
            
        Returns:
            List of recent predictions
        """
        try:
            # Sort by timestamp and get the most recent
            predictions = sorted(self.predictions, key=lambda p: p.get("timestamp", ""), reverse=True)
            return predictions[:limit]
        except Exception as e:
            logger.error(f"Error getting recent predictions: {str(e)}")
            return []
    
    def get_similar_healing_events(self, memory_stats, limit=5):
        """
        Get healing events similar to the current memory conditions.
        
        Args:
            memory_stats: Current memory statistics
            limit: Maximum number of events to return
            
        Returns:
            List of similar healing events
        """
        try:
            # Simple approach: get the most recent healing events
            events = sorted(self.healing_events, key=lambda e: e.get("timestamp", ""), reverse=True)
            return events[:limit]
        except Exception as e:
            logger.error(f"Error getting similar healing events: {str(e)}")
            return []