import os
import time
import logging
import threading
import json
import subprocess
from datetime import datetime

from .llm_utils import LLMProcessor
from .memory_core import get_memory_stats, release_memory_cache

logger = logging.getLogger(__name__)

class MemoryHealerAgent:
    """
    Agent responsible for implementing corrective actions to resolve memory issues.
    """
    
    def __init__(self, rag_pipeline=None):
        """
        Initialize the Memory Healer Agent.
        
        Args:
            rag_pipeline: The RAG pipeline for context-aware decisions
        """
        self.rag_pipeline = rag_pipeline
        self.running = False
        self.healer_thread = None
        self.healing_interval = 120
        self.llm_processor = LLMProcessor(
            model="mistral",
            api_key=os.environ.get("MISTRAL_API_KEY_HEALER"),
            cache_dir="data/healer_cache"
        )
        self.healing_history = []
        self.max_history_size = 100 
        logger.info("Memory Healer Agent initialized")
        
    def start_healing_service(self, interval=120):
        """
        Start healing service in a separate thread.
        
        Args:
            interval: Healing check interval in seconds
        """
        if self.running:
            logger.warning("Healing service is already running")
            return
            
        self.healing_interval = interval
        self.running = True
        
        self.healer_thread = threading.Thread(target=self._healing_loop)
        self.healer_thread.daemon = True
        self.healer_thread.start()
        
        logger.info(f"Memory healing service started with interval of {interval} seconds")
        
    def stop_healing_service(self):
        """Stop the healing service thread."""
        self.running = False
        if self.healer_thread:
            self.healer_thread.join(timeout=5.0)
        logger.info("Memory healing service stopped")
        
    def _healing_loop(self):
        """Main healing loop that runs in a separate thread."""
        while self.running:
            try:
                memory_stats = get_memory_stats()
                
                if self._should_execute_healing(memory_stats):
                    healing_plan = self.generate_healing_plan(memory_stats)
                    
                    if healing_plan and 'actions' in healing_plan and healing_plan['actions']:
                        results = self.execute_actions(healing_plan['actions'])
                        
                        validation = self.validate_healing_results(results)
                        
                        self._log_healing_event(memory_stats, healing_plan, results, validation)
                        
                        self._add_to_healing_history(memory_stats, healing_plan, results, validation)
                
                time.sleep(self.healing_interval)
                    
            except Exception as e:
                logger.error(f"Error in healing loop: {str(e)}")
                time.sleep(self.healing_interval)
    
    def _should_execute_healing(self, memory_stats):
        """
        Determine if healing actions should be executed based on current memory statistics.
        
        Args:
            memory_stats: Dictionary of current memory statistics
            
        Returns:
            Boolean indicating if healing is needed
        """
        used_percent = memory_stats.get('used_percent', 0)
        
        if used_percent > 80:
            return True
            
        if self.rag_pipeline:
            recent_predictions = self.rag_pipeline.get_recent_predictions(limit=1)
            if recent_predictions:
                prediction = recent_predictions[0]
                for issue in prediction.get('predicted_issues', []):
                    if issue.get('severity') == 'critical' and issue.get('probability', 0) > 0.7:
                        logger.info("Initiating preemptive healing based on critical prediction")
                        return True
                        
        return False
    
    def generate_healing_plan(self, memory_stats):
        """
        Generate a plan to resolve memory issues based on current statistics.
        
        Args:
            memory_stats: Dictionary of current memory statistics
            
        Returns:
            Dictionary containing the healing plan
        """
        try:
            healing_plan = {
                'timestamp': datetime.now().isoformat(),
                'memory_usage': memory_stats.get('used_percent', 0),
                'actions': []
            }
            
            used_percent = memory_stats.get('used_percent', 0)
            
            if used_percent > 95:
                healing_plan['severity'] = 'critical'
                healing_plan['actions'].append({
                    'action_type': 'clear_cache',
                    'description': 'Clear system cache to free memory',
                    'priority': 'high'
                })
                healing_plan['actions'].append({
                    'action_type': 'defragment',
                    'description': 'Perform memory defragmentation',
                    'priority': 'high'
                })
            elif used_percent > 85:
                healing_plan['severity'] = 'high'
                healing_plan['actions'].append({
                    'action_type': 'clear_cache',
                    'description': 'Clear system cache to free memory',
                    'priority': 'medium'
                })
            elif used_percent > 75:
                healing_plan['severity'] = 'moderate'
                healing_plan['actions'].append({
                    'action_type': 'optimize',
                    'description': 'Optimize memory usage',
                    'priority': 'low'
                })
                
            if self.llm_processor and self.rag_pipeline:
                historical_context = self.rag_pipeline.get_relevant_memory_events(memory_stats)
                healing_history = self.get_healing_history(limit=10)
                
                enhanced_plan = self._llm_enhanced_plan(memory_stats, historical_context, healing_history)
                
                if enhanced_plan:
                    if 'actions' in enhanced_plan and enhanced_plan['actions']:
                        healing_plan['actions'] = enhanced_plan['actions']
                    
                    for key, value in enhanced_plan.items():
                        if key != 'actions' and value:
                            healing_plan[key] = value
            
            return healing_plan
                
        except Exception as e:
            logger.error(f"Error generating healing plan: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'actions': [{
                    'action_type': 'clear_cache',
                    'description': 'Emergency cache clearing due to error',
                    'priority': 'high'
                }]
            }
    
    def execute_actions(self, actions):
        """
        Execute the healing actions from the healing plan.
        
        Args:
            actions: List of actions to execute
            
        Returns:
            Dictionary containing the results of executed actions
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'executed_actions': [],
            'memory_before': get_memory_stats(),
            'success': True
        }
        
        try:
            for action in actions:
                action_type = action.get('action_type')
                action_result = {
                    'action_type': action_type,
                    'description': action.get('description', ''),
                    'success': False,
                    'details': ''
                }
                
                try:
                    if action_type == 'clear_cache':
                        success = release_memory_cache()
                        action_result['success'] = success
                        action_result['details'] = 'Memory cache cleared successfully' if success else 'Failed to clear memory cache'
                        
                    elif action_type == 'defragment':
                        logger.info("Simulating memory defragmentation")
                        time.sleep(2) 
                        action_result['success'] = True
                        action_result['details'] = 'Memory defragmentation completed'
                        
                    elif action_type == 'optimize':
                        logger.info("Simulating memory optimization")
                        time.sleep(1)  
                        action_result['success'] = True
                        action_result['details'] = 'Memory optimization completed'
                        
                    elif action_type == 'custom_command' and 'command' in action:
                        command = action.get('command')
                        allowed_commands = ['sync', 'echo 3 > /proc/sys/vm/drop_caches']
                        
                        if command in allowed_commands:
                            subprocess.run(command, shell=True, check=True)
                            action_result['success'] = True
                            action_result['details'] = f'Custom command executed: {command}'
                        else:
                            action_result['details'] = f'Command not in allowed list: {command}'
                    
                    else:
                        action_result['details'] = f'Unknown action type: {action_type}'
                        
                except Exception as action_error:
                    action_result['success'] = False
                    action_result['details'] = f'Error executing action: {str(action_error)}'
                    logger.error(f"Error executing action {action_type}: {str(action_error)}")
                
                results['executed_actions'].append(action_result)
                
                if not action_result['success']:
                    results['success'] = False
            
            results['memory_after'] = get_memory_stats()
            results['memory_change'] = {
                'before_percent': results['memory_before'].get('used_percent', 0),
                'after_percent': results['memory_after'].get('used_percent', 0),
                'difference': results['memory_before'].get('used_percent', 0) - results['memory_after'].get('used_percent', 0)
            }
            
            return results
                
        except Exception as e:
            logger.error(f"Error executing healing actions: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
            results['memory_after'] = get_memory_stats()
            return results
    
    def validate_healing_results(self, results):
        """
        Validate the effectiveness of the healing actions.
        
        Args:
            results: Dictionary containing the results of executed actions
            
        Returns:
            Dictionary containing validation results
        """
        validation = {
            'timestamp': datetime.now().isoformat(),
            'effective': False,
            'details': ''
        }
        
        try:
            before_percent = results.get('memory_before', {}).get('used_percent', 0)
            after_percent = results.get('memory_after', {}).get('used_percent', 0)
            difference = before_percent - after_percent
            
            if difference > 10:
                validation['effective'] = True
                validation['effectiveness_score'] = 0.9
                validation['details'] = f'Highly effective: Memory usage decreased by {difference:.2f}%'
            elif difference > 5:
                validation['effective'] = True
                validation['effectiveness_score'] = 0.7
                validation['details'] = f'Moderately effective: Memory usage decreased by {difference:.2f}%'
            elif difference > 0:
                validation['effective'] = True
                validation['effectiveness_score'] = 0.3
                validation['details'] = f'Slightly effective: Memory usage decreased by {difference:.2f}%'
            else:
                validation['effective'] = False
                validation['effectiveness_score'] = 0.0
                validation['details'] = f'Not effective: Memory usage did not decrease (change: {difference:.2f}%)'
            
            return validation
                
        except Exception as e:
            logger.error(f"Error validating healing results: {str(e)}")
            validation['effective'] = False
            validation['details'] = f'Error during validation: {str(e)}'
            return validation
    
    def _log_healing_event(self, memory_stats, healing_plan, results, validation):
        """
        Log healing event to a file for persistence.
        
        Args:
            memory_stats: Memory statistics before healing
            healing_plan: Healing plan that was executed
            results: Results of the executed actions
            validation: Validation of healing effectiveness
        """
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'memory_stats': memory_stats,
                'healing_plan': healing_plan,
                'results': results,
                'validation': validation
            }
            
            with open('data/healing_events.jsonl', 'a') as f:
                f.write(json.dumps(event) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging healing event: {str(e)}")
    
    def _add_to_healing_history(self, memory_stats, healing_plan, results, validation):
        """
        Add healing event to in-memory history.
        
        Args:
            memory_stats: Memory statistics before healing
            healing_plan: Healing plan that was executed
            results: Results of the executed actions
            validation: Validation of healing effectiveness
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'memory_usage': memory_stats.get('used_percent', 0),
            'actions': [action.get('action_type') for action in healing_plan.get('actions', [])],
            'effective': validation.get('effective', False),
            'effectiveness_score': validation.get('effectiveness_score', 0.0)
        }
        
        self.healing_history.append(event)
        if len(self.healing_history) > self.max_history_size:
            self.healing_history = self.healing_history[-self.max_history_size:]
    
    def get_healing_history(self, limit=None):
        """
        Get healing history events.
        
        Args:
            limit: Maximum number of events to return (default: all)
            
        Returns:
            List of healing history events
        """
        if limit:
            return self.healing_history[-limit:]
        return self.healing_history
    
    def _llm_enhanced_plan(self, memory_stats, historical_context, healing_history):
        """
        Generate an enhanced healing plan using LLM.
        
        Args:
            memory_stats: Current memory statistics
            historical_context: Historical memory events for context
            healing_history: Previous healing actions and their effectiveness
            
        Returns:
            Enhanced healing plan from the LLM
        """
        try:
            simplified_history = []
            for event in historical_context[-5:]:  
                simplified_event = {
                    'timestamp': event.get('timestamp', ''),
                    'used_percent': event.get('stats', {}).get('used_percent', 0),
                    'anomaly': event.get('analysis', {}).get('anomaly_detected', False)
                }
                simplified_history.append(simplified_event)
            
            simplified_healing = []
            for event in healing_history[-5:]:  
                simplified_healing.append({
                    'timestamp': event.get('timestamp', ''),
                    'actions': event.get('actions', []),
                    'effective': event.get('effective', False),
                    'effectiveness_score': event.get('effectiveness_score', 0.0)
                })
            
            prompt = f"""
            You are a memory healing expert. Based on the current memory statistics, historical data, and past healing actions, generate a healing plan to resolve memory issues.
            
            Current Memory Statistics:
            {json.dumps(memory_stats, indent=2)}
            
            Historical Memory Events:
            {json.dumps(simplified_history, indent=2)}
            
            Previous Healing Actions and Their Effectiveness:
            {json.dumps(simplified_healing, indent=2)}
            
            Available action types:
            - clear_cache: Clear system memory cache
            - defragment: Perform memory defragmentation
            - optimize: Optimize memory usage patterns
            - custom_command: Execute a custom command (limited to safe operations)
            
            Generate a healing plan with specific actions to resolve current memory issues. Consider the effectiveness of previous actions.
            
            Format your response as a JSON object with the following fields:
            - severity: (string) critical/high/moderate/low
            - description: (string) An explanation of the healing plan
            - actions: (array of objects) List of actions with fields:
              - action_type: (string) Type of action to perform
              - description: (string) Description of what this action will do
              - priority: (string) high/medium/low
              - command: (string, optional) For custom_command type only, specify command
            - expected_improvement: (number) Expected percentage improvement in memory usage
            """
            
            response = self.llm_processor.process(prompt)
            
            try:
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    json_str = response.split("```")[1].strip()
                    
                enhanced_plan = json.loads(json_str)
                
                if 'actions' in enhanced_plan:
                    safe_actions = []
                    for action in enhanced_plan['actions']:
                        if action.get('action_type') in ['clear_cache', 'defragment', 'optimize', 'custom_command']:
                            if action.get('action_type') == 'custom_command' and 'command' in action:
                                command = action.get('command')
                                allowed_commands = ['sync', 'echo 3 > /proc/sys/vm/drop_caches']
                                if command not in allowed_commands:
                                    continue
                            safe_actions.append(action)
                    
                    enhanced_plan['actions'] = safe_actions
                
                return enhanced_plan
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON, using basic healing plan")
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM-enhanced healing plan: {str(e)}")
            return {}
        
    def generate_urgent_healing_plan(self):
        """
        Generate an urgent healing plan for critical memory conditions.
        
        Returns:
            Dictionary containing the urgent healing plan
        """
        memory_stats = get_memory_stats()
        
        healing_plan = {
            'timestamp': datetime.now().isoformat(),
            'severity': 'critical',
            'description': 'Urgent healing plan for critical memory condition',
            'actions': [
                {
                    'action_type': 'clear_cache',
                    'description': 'Emergency cache clearing to free memory',
                    'priority': 'high'
                },
                {
                    'action_type': 'defragment',
                    'description': 'Emergency memory defragmentation',
                    'priority': 'high'
                }
            ]
        }
        
        return healing_plan
        
    def execute_priority_actions(self, healing_plan):
        """
        Execute only high-priority actions from a healing plan.
        
        Args:
            healing_plan: Healing plan containing actions
            
        Returns:
            Results of executed actions
        """
        priority_actions = [action for action in healing_plan.get('actions', []) 
                           if action.get('priority') == 'high']
        
        return self.execute_actions(priority_actions)
