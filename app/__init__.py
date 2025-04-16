import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app(config=None):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_replace_in_production")
    
    disable_db = os.environ.get("DISABLE_DATABASE", "").lower() == "true"
    
    if not disable_db:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///data/memory_system.db")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        if config:
            app.config.update(config)
        
        db.init_app(app)
        
        with app.app_context():
            from models import MemoryEvent, MemoryPrediction, HealingEvent
            db.create_all()
    else:
        logger.info("Database functionality disabled")
        
        if config:
            filtered_config = {k: v for k, v in config.items() if not k.startswith('SQLALCHEMY_')}
            app.config.update(filtered_config)
    
    return app