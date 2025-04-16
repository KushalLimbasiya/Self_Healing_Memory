from datetime import datetime
import json
from sqlalchemy.dialects.postgresql import JSONB

# Database instance is imported from app package
from app import db

class MemoryEvent(db.Model):
    """Model for storing memory monitoring events."""
    __tablename__ = 'memory_events'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    stats = db.Column(JSONB, nullable=False)
    analysis = db.Column(JSONB, nullable=True)
    
    def __repr__(self):
        return f'<MemoryEvent id={self.id} timestamp={self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'stats': self.stats,
            'analysis': self.analysis
        }
    
    @classmethod
    def from_json(cls, json_data):
        """Create a MemoryEvent instance from JSON data."""
        timestamp = datetime.fromisoformat(json_data.get('timestamp')) if 'timestamp' in json_data else datetime.utcnow()
        return cls(
            timestamp=timestamp,
            stats=json_data.get('stats', {}),
            analysis=json_data.get('analysis', {})
        )


class MemoryPrediction(db.Model):
    """Model for storing memory predictions."""
    __tablename__ = 'memory_predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    current_memory_used = db.Column(db.Float, nullable=False)
    predicted_memory_usage_1h = db.Column(db.Float, nullable=True)
    predicted_memory_usage_24h = db.Column(db.Float, nullable=True)
    predicted_issues = db.Column(JSONB, nullable=True)
    
    def __repr__(self):
        return f'<MemoryPrediction id={self.id} timestamp={self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'current_memory_used': self.current_memory_used,
            'predicted_memory_usage_1h': self.predicted_memory_usage_1h,
            'predicted_memory_usage_24h': self.predicted_memory_usage_24h,
            'predicted_issues': self.predicted_issues
        }
    
    @classmethod
    def from_json(cls, json_data):
        """Create a MemoryPrediction instance from JSON data."""
        timestamp = datetime.fromisoformat(json_data.get('timestamp')) if 'timestamp' in json_data else datetime.utcnow()
        return cls(
            timestamp=timestamp,
            current_memory_used=json_data.get('current_memory_used', 0),
            predicted_memory_usage_1h=json_data.get('predicted_memory_usage_1h'),
            predicted_memory_usage_24h=json_data.get('predicted_memory_usage_24h'),
            predicted_issues=json_data.get('predicted_issues', [])
        )


class HealingEvent(db.Model):
    """Model for storing memory healing events."""
    __tablename__ = 'healing_events'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    memory_stats = db.Column(JSONB, nullable=False)
    healing_plan = db.Column(JSONB, nullable=True)
    results = db.Column(JSONB, nullable=True)
    validation = db.Column(JSONB, nullable=True)
    
    def __repr__(self):
        return f'<HealingEvent id={self.id} timestamp={self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'memory_stats': self.memory_stats,
            'healing_plan': self.healing_plan,
            'results': self.results,
            'validation': self.validation
        }
    
    @classmethod
    def from_json(cls, json_data):
        """Create a HealingEvent instance from JSON data."""
        timestamp = datetime.fromisoformat(json_data.get('timestamp')) if 'timestamp' in json_data else datetime.utcnow()
        return cls(
            timestamp=timestamp,
            memory_stats=json_data.get('memory_stats', {}),
            healing_plan=json_data.get('healing_plan'),
            results=json_data.get('results'),
            validation=json_data.get('validation')
        )