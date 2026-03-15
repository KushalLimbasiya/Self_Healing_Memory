import os
import sys
import logging
from flask import Flask


def _create_stream_handler() -> logging.StreamHandler:
    """StreamHandler with UTF-8 encoding so → and ⚠️ don't crash on Windows."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    # Force UTF-8 on Windows terminals (cp1252 cannot encode → or emoji)
    if hasattr(handler.stream, "reconfigure"):
        try:
            handler.stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    return handler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/system.log", mode="a", encoding="utf-8"),
        _create_stream_handler(),
    ],
)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = os.environ.get("SESSION_SECRET", "shm-dev-secret")
    # Always reload templates from disk so HTML changes apply without restart
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    return app