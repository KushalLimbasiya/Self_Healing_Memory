import os
import time
import logging
import threading
import json
from datetime import datetime, timedelta

from .llm_utils import LLMProcessor
from .memory_core import get_memory_stats

logger = logging.getLogger(__name__)

class MemoryPredictorAgent:
    """
    Agent responsible for predicting future memory conditions based on historical data.
    """
    
    def __init__(self, rag_pipeline=None):
        """
        Initialize the Memory Predictor Agent.
        
        Args:
            rag_pipeline: The RAG pipeline for context-aware decisions
        """
        self.rag_pipeline = rag_pipeline
        self.running = False
        self.predictor_thread = None
        self.prediction_interval = 300  # Default prediction interval in seconds (5 minutes)
        self.llm_processor = LLMProcessor(
            model="mistral",
            api_key=os.environ.get("MISTRAL_API_KEY_PREDICTOR"),
            cache_dir="data/predictor_cache"
        )
        self.latest_prediction = None
        logger.info("Memory Predictor Agent initialized")
        
    def start_prediction_service(self, interval=300):
        """
        Start prediction service in a separate thread.
        
        Args:
            interval: Prediction interval in seconds
        """
        if self.running:
            logger.warning("Prediction service is already running")
            return
            
        self.prediction_interval = interval
        self.running = True
        
        self.predictor_thread = threading.Thread(target=self._prediction_loop)
        self.predictor_thread.daemon = True
        self.predictor_thread.start()
        
        logger.info(f"Memory prediction service started with interval of {interval} seconds")
        
    def stop_prediction_service(self):
        """Stop the prediction service thread."""
        self.running = False
        if self.predictor_thread:
            self.predictor_thread.join(timeout=5.0)
        logger.info("Memory prediction service stopped")
        
    def _prediction_loop(self):
        """Main prediction loop that runs in a separate thread."""
        while self.running:
            try:
                # Get current memory statistics
                memory_stats = get_memory_stats()
                
                # Retrieve historical data using RAG pipeline
                if self.rag_pipeline:
                    historical_data = self.rag_pipeline.get_relevant_memory_events(
                        memory_stats, 
                        limit=20,
                        time_window=3600  # Last hour
                    )
                else:
                    # If RAG pipeline is not available, use a simple approach to load recent events
                    historical_data = self._load_recent_events(20)
                
                # Generate prediction
                prediction = self.predict_memory_condition(memory_stats, historical_data)
                
                # Store the latest prediction
                self.latest_prediction = prediction
                
                # Log the prediction
                self._log_prediction(prediction)
                
                # Sleep until next prediction
                time.sleep(self.prediction_interval)
                    
            except Exception as e:
                logger.error(f"Error in prediction loop: {str(e)}")
                time.sleep(self.prediction_interval)
    
    def predict_memory_condition(self, current_stats, historical_data):
        """
        Predict future memory conditions based on current statistics and historical data.
        
        Args:
            current_stats: Dictionary of current memory statistics
            historical_data: List of historical memory events
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            # Basic prediction without LLM
            prediction = {
                'timestamp': datetime.now().isoformat(),
                'current_memory_used': current_stats.get('used_percent', 0),
                'prediction_timeframe': '1 hour',
                'predicted_issues': []
            }
            
            # Simple trend analysis
            if len(historical_data) >= 3:
                # Calculate trend from the last few data points
                recent_values = [event.get('stats', {}).get('used_percent', 0) for event in historical_data[-3:]]
                if all(recent_values):
                    trend = sum([(recent_values[i] - recent_values[i-1]) for i in range(1, len(recent_values))]) / (len(recent_values) - 1)
                    
                    # Extrapolate the trend
                    current_value = current_stats.get('used_percent', 0)
                    predicted_value_1h = current_value + (trend * (3600 / self.prediction_interval))
                    
                    prediction['predicted_memory_usage_1h'] = min(100, max(0, predicted_value_1h))
                    
                    # Add prediction details
                    if predicted_value_1h > 90:
                        prediction['predicted_issues'].append({
                            'severity': 'critical',
                            'description': 'Critical memory shortage predicted within 1 hour',
                            'probability': 0.8,
                            'timeframe': '1 hour'
                        })
                    elif predicted_value_1h > 80:
                        prediction['predicted_issues'].append({
                            'severity': 'high',
                            'description': 'High memory usage predicted within 1 hour',
                            'probability': 0.7,
                            'timeframe': '1 hour'
                        })
            
            # Enhance prediction with LLM if available
            if self.llm_processor:
                enhanced_prediction = self._llm_enhanced_prediction(current_stats, historical_data)
                # Merge the enhanced prediction with the basic one
                if enhanced_prediction:
                    for key, value in enhanced_prediction.items():
                        if key not in prediction or value:  # Only update if the field exists and has a value
                            prediction[key] = value
            
            return prediction
                
        except Exception as e:
            logger.error(f"Error predicting memory condition: {str(e)}")
            # Return basic prediction in case of error
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'predicted_issues': []
            }
    
    def _llm_enhanced_prediction(self, current_stats, historical_data):
        """
        Enhance memory prediction using LLM.
        
        Args:
            current_stats: Current memory statistics
            historical_data: Historical memory events for context
            
        Returns:
            Enhanced prediction from the LLM
        """
        try:
            # Prepare a simplified version of historical data to keep prompt size manageable
            simplified_history = []
            for event in historical_data[-10:]:  # Use only the most recent 10 events
                simplified_event = {
                    'timestamp': event.get('timestamp', ''),
                    'used_percent': event.get('stats', {}).get('used_percent', 0),
                    'free': event.get('stats', {}).get('free', 0),
                    'anomaly': event.get('analysis', {}).get('anomaly_detected', False)
                }
                simplified_history.append(simplified_event)
            
            prompt = f"""
            You are a memory usage prediction expert. Based on the current memory statistics and historical data, predict future memory conditions for the next hour and 24 hours.
            
            Current Memory Statistics:
            {json.dumps(current_stats, indent=2)}
            
            Historical Memory Data (most recent first):
            {json.dumps(simplified_history, indent=2)}
            
            Provide a detailed prediction including:
            1. Predicted memory usage in 1 hour (percent)
            2. Predicted memory usage in 24 hours (percent)
            3. List of potential issues that might arise, with severity, probability, and timeframe
            4. Recommended actions to prevent potential issues
            
            Format your response as a JSON object with the following fields:
            - predicted_memory_usage_1h (number)
            - predicted_memory_usage_24h (number)
            - predicted_issues (list of objects with severity, description, probability, timeframe)
            - recommendations (list of strings)
            - confidence_score (number between 0 and 1)
            """
            
            response = self.llm_processor.process(prompt)
            
            # Extract JSON from the response
            try:
                # Find JSON block in response (in case the LLM added other text)
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].strip()
                    
                enhanced_prediction = json.loads(json_str)
                return enhanced_prediction
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON, using basic prediction")
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM-enhanced prediction: {str(e)}")
            return {}
    
    def _log_prediction(self, prediction):
        """
        Log prediction to a file for persistence.
        
        Args:
            prediction: Prediction results
        """
        try:
            with open('data/memory_predictions.jsonl', 'a') as f:
                f.write(json.dumps(prediction) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging prediction: {str(e)}")
    
    def _load_recent_events(self, limit=20):
        """
        Load recent memory events from the log file when RAG pipeline is not available.
        
        Args:
            limit: Maximum number of events to load
            
        Returns:
            List of recent memory events
        """
        events = []
        try:
            if os.path.exists('data/memory_events.jsonl'):
                with open('data/memory_events.jsonl', 'r') as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        events.append(json.loads(line.strip()))
        except Exception as e:
            logger.error(f"Error loading recent memory events: {str(e)}")
        
        return events
    
    def get_latest_prediction(self):
        """
        Get the most recent prediction.
        
        Returns:
            Dictionary containing the latest prediction or None if no prediction available
        """
        return self.latest_prediction
