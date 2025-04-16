import os
import time
import logging
import threading
import json
import subprocess
from datetime import datetime

from .llm_utils import LLMProcessor
from .memory_core import get_memory_stats

logger = logging.getLogger(__name__)

class MemoryMonitorAgent:
    """
    Agent responsible for monitoring memory conditions and detecting anomalies.
    """
    
    def __init__(self, rag_pipeline=None):
        """
        Initialize the Memory Monitor Agent.
        
        Args:
            rag_pipeline: The RAG pipeline for context-aware decisions
        """
        self.rag_pipeline = rag_pipeline
        self.running = False
        self.monitor_thread = None
        self.monitor_interval = 60  
        self.llm_processor = LLMProcessor(
            model="mistral",
            api_key=os.environ.get("MISTRAL_API_KEY_MONITOR"),
            cache_dir="data/monitor_cache"
        )
        self.memory_threshold = 0.8  
        logger.info("Memory Monitor Agent initialized")
        
    def start_monitoring(self, interval=60):
        """
        Start monitoring memory conditions in a separate thread.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.running:
            logger.warning("Monitoring is already running")
            return
            
        self.monitor_interval = interval
        self.running = True
        
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Memory monitoring started with interval of {interval} seconds")
        
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Memory monitoring stopped")
        
    def _monitoring_loop(self):
        """Main monitoring loop that runs in a separate thread."""
        while self.running:
            try:
                memory_stats = get_memory_stats()
                
                analysis = self.analyze_memory_conditions(memory_stats)
                
                self._log_memory_event(memory_stats, analysis)
                
                if self.rag_pipeline:
                    self.rag_pipeline.add_memory_event(memory_stats, analysis)
                
                if analysis.get('anomaly_detected', False):
                    logger.warning(f"Memory anomaly detected: {analysis.get('anomaly_description')}")
                
                if memory_stats.get('used_percent', 0) > 90:
                    time.sleep(max(10, self.monitor_interval // 3))
                else:
                    time.sleep(self.monitor_interval)
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.monitor_interval)
    
    def analyze_memory_conditions(self, memory_stats):
        """
        Analyze memory conditions to detect anomalies and potential issues.
        
        Args:
            memory_stats: Dictionary of memory statistics
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            used_percent = memory_stats.get('used_percent', 0)
            free_memory = memory_stats.get('free', 0)
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'anomaly_detected': False,
                'severity': 'normal',
                'usage_level': 'normal',
                'recommendation': None
            }
            
            if used_percent > 90:
                analysis['usage_level'] = 'critical'
            elif used_percent > 80:
                analysis['usage_level'] = 'high'
            elif used_percent > 60:
                analysis['usage_level'] = 'moderate'
                
            if used_percent > 90 and free_memory < 500 * 1024 * 1024:  # Less than 500MB free
                analysis['anomaly_detected'] = True
                analysis['severity'] = 'critical'
                analysis['anomaly_description'] = 'Critical memory shortage detected'
                analysis['recommendation'] = 'Immediate memory cleanup required'
            elif used_percent > 80:
                analysis['anomaly_detected'] = True
                analysis['severity'] = 'high'
                analysis['anomaly_description'] = 'High memory usage detected'
                analysis['recommendation'] = 'Consider freeing unused memory'
                
            if self.llm_processor and self.rag_pipeline:
                historical_context = self.rag_pipeline.get_relevant_memory_events(memory_stats)
                enhanced_analysis = self._llm_enhanced_analysis(memory_stats, historical_context)
                analysis.update(enhanced_analysis)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing memory conditions: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'anomaly_detected': False,
                'severity': 'unknown',
                'error': str(e)
            }
    
    def _llm_enhanced_analysis(self, memory_stats, historical_context):
        """
        Enhance memory analysis using LLM.
        
        Args:
            memory_stats: Current memory statistics
            historical_context: Historical memory events for context
            
        Returns:
            Enhanced analysis from the LLM
        """
        try:
            prompt = f"""
            You are a memory analysis expert. Analyze the following memory statistics and determine if there are any anomalies, potential issues, or patterns that should be addressed.
            
            Current Memory Statistics:
            {json.dumps(memory_stats, indent=2)}
            
            Historical Context (previous memory events):
            {json.dumps(historical_context, indent=2)}
            
            Provide a detailed analysis including:
            1. Is there an anomaly? (true/false)
            2. What is the severity? (normal/low/moderate/high/critical)
            3. Detailed description of any issues detected
            4. Specific recommendations for addressing the issues
            5. Patterns observed in memory usage over time
            
            Format your response as a JSON object with the following fields:
            - anomaly_detected (boolean)
            - severity (string)
            - anomaly_description (string, null if no anomaly)
            - recommendations (list of strings)
            - patterns_observed (list of strings)
            """
            
            response = self.llm_processor.process(prompt)
            
            try:
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].strip()
                    
                enhanced_analysis = json.loads(json_str)
                return enhanced_analysis
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON, using basic analysis")
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM-enhanced analysis: {str(e)}")
            return {}
    
    def _log_memory_event(self, memory_stats, analysis):
        """
        Log memory event to a file for persistence.
        
        Args:
            memory_stats: Memory statistics
            analysis: Analysis results
        """
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'stats': memory_stats,
                'analysis': analysis
            }
            
            with open('data/memory_events.jsonl', 'a') as f:
                f.write(json.dumps(event) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging memory event: {str(e)}")
    
    def is_memory_critical(self):
        """
        Check if the current memory condition is critical.
        
        Returns:
            Boolean indicating if memory is in a critical state
        """
        memory_stats = get_memory_stats()
        used_percent = memory_stats.get('used_percent', 0)
        return used_percent > 90
