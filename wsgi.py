"""
WSGI Entry Point for Production Deployment
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the Flask application
from run import app as application

# Configure for production
if __name__ != "__main__":
    # Production configuration
    application.config['DEBUG'] = False
    application.config['TESTING'] = False
    
    # Set production logging
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Ensure logs directory exists
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Set up file logging
    if not application.debug and not application.testing:
        file_handler = RotatingFileHandler(
            str(log_dir / 'homegrubhub_production.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        application.logger.addHandler(file_handler)
        application.logger.setLevel(logging.INFO)
        application.logger.info('HomeGrubHub production startup')

if __name__ == "__main__":
    # Development mode when run directly
    application.logger.info("Starting HomeGrubHub in development mode...")
    application.run(host='127.0.0.1', port=8052, debug=True)
