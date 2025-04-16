import os
import logging
import json
from datetime import datetime, timedelta
import threading
from flask import render_template, jsonify, request, current_app
from app.monitor_agent import MemoryMonitorAgent
from app.predictor_agent import MemoryPredictorAgent
from app.healer_agent import MemoryHealerAgent
from app.memory_core import get_memory_stats, simulate_memory_usage
from app import create_app, db
from models import MemoryEvent, MemoryPrediction, HealingEvent

# Create Flask app
app = create_app()

# Configure logging
logger = logging.getLogger(__name__)

# Global references to agents
monitor_agent = None
predictor_agent = None
healer_agent = None

# Store memory data for charts
memory_history = []
MAX_HISTORY_POINTS = 100

def initialize_agents():
    """Initialize agent instances for the web interface."""
    global monitor_agent, predictor_agent, healer_agent
    
    if not monitor_agent:
        # These are separate instances from the ones in main.py
        # They are used only for handling web interface requests
        monitor_agent = MemoryMonitorAgent()
        predictor_agent = MemoryPredictorAgent()
        healer_agent = MemoryHealerAgent()
        
        logger.info("Web interface agent references initialized")

# Initialize agents on startup
with app.app_context():
    initialize_agents()

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('grafana_dashboard.html')

@app.route('/dashboard')
def dashboard():
    """Render the main dashboard page."""
    return render_template('grafana_dashboard.html')

@app.route('/legacy')
def legacy_dashboard():
    """Render the legacy dashboard page."""
    return render_template('index.html')

@app.route('/api/memory/current')
def get_current_memory():
    """API endpoint to get current memory statistics."""
    try:
        stats = get_memory_stats()
        
        # Add to history
        global memory_history
        memory_history.append({
            'timestamp': datetime.now().isoformat(),
            'used_percent': stats.get('used_percent', 0)
        })
        
        # Trim history if needed
        if len(memory_history) > MAX_HISTORY_POINTS:
            memory_history = memory_history[-MAX_HISTORY_POINTS:]
            
        return jsonify(success=True, data=stats)
    except Exception as e:
        logger.error(f"Error getting memory stats: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/memory/history')
def get_memory_history():
    """API endpoint to get memory usage history."""
    try:
        return jsonify(success=True, data=memory_history)
    except Exception as e:
        logger.error(f"Error getting memory history: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/memory/analyze', methods=['POST'])
def analyze_memory():
    """API endpoint to analyze current memory conditions."""
    try:
        # Make sure agents are initialized
        initialize_agents()
        
        # Get memory statistics
        stats = get_memory_stats()
        
        # Perform analysis
        analysis = monitor_agent.analyze_memory_conditions(stats)
        
        # Save to database
        with app.app_context():
            # Create a new memory event
            memory_event = MemoryEvent(
                stats=stats,
                analysis=analysis
            )
            db.session.add(memory_event)
            db.session.commit()
            logger.info(f"Saved memory event to database: id={memory_event.id}")
        
        # Also save to file for backward compatibility
        with open('data/memory_events.jsonl', 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'stats': stats,
                'analysis': analysis
            }) + '\n')
        
        return jsonify(success=True, stats=stats, analysis=analysis)
    except Exception as e:
        logger.error(f"Error analyzing memory: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/memory/predict', methods=['POST'])
def predict_memory():
    """API endpoint to predict future memory conditions."""
    try:
        # Make sure agents are initialized
        initialize_agents()
        
        # Get memory statistics
        stats = get_memory_stats()
        
        # Load recent events from database
        recent_events = []
        with app.app_context():
            # Get the 20 most recent memory events
            db_events = MemoryEvent.query.order_by(MemoryEvent.timestamp.desc()).limit(20).all()
            recent_events = [event.to_dict() for event in db_events]
        
        # Generate prediction
        prediction = predictor_agent.predict_memory_condition(stats, recent_events)
        
        # Save prediction to database
        with app.app_context():
            # Create a new memory prediction
            memory_prediction = MemoryPrediction(
                current_memory_used=stats.get('used_percent', 0),
                predicted_memory_usage_1h=prediction.get('predicted_usage_1h', None),
                predicted_memory_usage_24h=prediction.get('predicted_usage_24h', None),
                predicted_issues=prediction.get('potential_issues', [])
            )
            db.session.add(memory_prediction)
            db.session.commit()
            logger.info(f"Saved memory prediction to database: id={memory_prediction.id}")
        
        # Also save to file for backward compatibility
        with open('data/memory_predictions.jsonl', 'a') as f:
            f.write(json.dumps({
                'timestamp': datetime.now().isoformat(),
                'stats': stats,
                'prediction': prediction
            }) + '\n')
        
        return jsonify(success=True, stats=stats, prediction=prediction)
    except Exception as e:
        logger.error(f"Error predicting memory: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/memory/heal', methods=['POST'])
def heal_memory():
    """API endpoint to execute healing actions."""
    try:
        # Make sure agents are initialized
        initialize_agents()
        
        # Get memory statistics
        stats = get_memory_stats()
        
        # Generate healing plan
        healing_plan = healer_agent.generate_healing_plan(stats)
        
        # Execute actions if requested
        execute = request.json.get('execute', False)
        results = None
        validation = None
        
        if execute and healing_plan and 'actions' in healing_plan and healing_plan['actions']:
            results = healer_agent.execute_actions(healing_plan['actions'])
            validation = healer_agent.validate_healing_results(results)
            
            # Save healing event to database
            with app.app_context():
                healing_event = HealingEvent(
                    memory_stats=stats,
                    healing_plan=healing_plan,
                    results=results,
                    validation=validation
                )
                db.session.add(healing_event)
                db.session.commit()
                logger.info(f"Saved healing event to database: id={healing_event.id}")
            
            # Also save to file for backward compatibility
            with open('data/healing_events.jsonl', 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'memory_stats': stats,
                    'healing_plan': healing_plan,
                    'results': results,
                    'validation': validation
                }) + '\n')
        
        return jsonify(
            success=True, 
            stats=stats, 
            healing_plan=healing_plan,
            executed=execute,
            results=results,
            validation=validation
        )
    except Exception as e:
        logger.error(f"Error healing memory: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/memory/simulate', methods=['POST'])
def simulate_memory():
    """API endpoint to simulate memory usage for testing."""
    try:
        # Get parameters
        usage_mb = request.json.get('usage_mb', 100)
        
        # Limit to reasonable values
        usage_mb = max(10, min(500, usage_mb))
        
        # Run simulation in a separate thread to avoid blocking
        def run_simulation():
            try:
                simulate_memory_usage(usage_mb)
            except Exception as e:
                logger.error(f"Error in memory simulation: {str(e)}")
        
        simulation_thread = threading.Thread(target=run_simulation)
        simulation_thread.daemon = True
        simulation_thread.start()
        
        return jsonify(
            success=True,
            message=f"Started memory usage simulation using {usage_mb}MB"
        )
    except Exception as e:
        logger.error(f"Error starting memory simulation: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/logs/memory', methods=['GET'])
def get_memory_logs():
    """API endpoint to get recent memory event logs."""
    try:
        limit = int(request.args.get('limit', 20))
        logs = []
        
        # Get events from database
        with app.app_context():
            db_events = MemoryEvent.query.order_by(MemoryEvent.timestamp.desc()).limit(limit).all()
            logs = [event.to_dict() for event in db_events]
        
        # Fallback to file if no database records
        if not logs and os.path.exists('data/memory_events.jsonl'):
            with open('data/memory_events.jsonl', 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    logs.append(json.loads(line.strip()))
        
        return jsonify(success=True, logs=logs)
    except Exception as e:
        logger.error(f"Error getting memory logs: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/logs/healing', methods=['GET'])
def get_healing_logs():
    """API endpoint to get recent healing event logs."""
    try:
        limit = int(request.args.get('limit', 20))
        logs = []
        
        # Get events from database
        with app.app_context():
            db_events = HealingEvent.query.order_by(HealingEvent.timestamp.desc()).limit(limit).all()
            logs = [event.to_dict() for event in db_events]
        
        # Fallback to file if no database records
        if not logs and os.path.exists('data/healing_events.jsonl'):
            with open('data/healing_events.jsonl', 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    logs.append(json.loads(line.strip()))
        
        return jsonify(success=True, logs=logs)
    except Exception as e:
        logger.error(f"Error getting healing logs: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/api/logs/predictions', methods=['GET'])
def get_prediction_logs():
    """API endpoint to get recent prediction logs."""
    try:
        limit = int(request.args.get('limit', 20))
        logs = []
        
        # Get predictions from database
        with app.app_context():
            db_predictions = MemoryPrediction.query.order_by(MemoryPrediction.timestamp.desc()).limit(limit).all()
            logs = [prediction.to_dict() for prediction in db_predictions]
        
        # Fallback to file if no database records
        if not logs and os.path.exists('data/memory_predictions.jsonl'):
            with open('data/memory_predictions.jsonl', 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    logs.append(json.loads(line.strip()))
        
        return jsonify(success=True, logs=logs)
    except Exception as e:
        logger.error(f"Error getting prediction logs: {str(e)}")
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
