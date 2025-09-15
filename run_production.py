"""
Production server startup using Waitress (Windows-compatible)
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_production_server():
    """Start the production server with Waitress"""
    logger = logging.getLogger("HomeGrubHub")
    try:
        from waitress import serve
        from wsgi import application

        # Reuse application's logging handlers
        logger.handlers = application.logger.handlers
        # Ensure logs also stream to console for operator visibility
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        logger.addHandler(stream_handler)
        
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'
        os.environ['ENVIRONMENT'] = 'production'
        
        # Ensure logs directory exists
        log_dir = project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        logger.info("Starting HomeGrubHub Production Server")
        logger.info("=========================================")
        logger.info("Server: http://127.0.0.1:8050")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        # Start Waitress server
        serve(
            application,
            host='127.0.0.1',
            port=8050,
            threads=6,  # Number of threads
            connection_limit=100,  # Max concurrent connections
            cleanup_interval=30,  # Cleanup interval in seconds
            channel_timeout=120,  # Channel timeout
            log_socket_errors=True,
            # URL scheme for reverse proxy
            url_scheme='http'
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except ImportError as e:
        # Fallback logger in case application failed to import
        logger.error("Failed to import application or dependencies: %s", e)
        logger.error("Please install: python -m pip install waitress")
        sys.exit(1)
    except Exception as e:
        # Ensure unexpected exceptions are logged
        logger.error("Error starting server: %s", e)
        logger.exception("Error starting server")
        sys.exit(1)

if __name__ == "__main__":
    start_production_server()
