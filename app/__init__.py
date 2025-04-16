import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

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

# Set up database
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app():
    # Create a Flask application
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_replace_in_production")
    
    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the app with the database extension
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        # Import models to create tables
        from models import MemoryEvent, MemoryPrediction, HealingEvent
        db.create_all()
    
    return app