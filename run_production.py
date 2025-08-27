"""
Production server startup using Waitress (Windows-compatible)
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def start_production_server():
    """Start the production server with Waitress"""
    try:
        from waitress import serve
        from wsgi import application
        
        # Set production environment
        os.environ['FLASK_ENV'] = 'production'
        os.environ['ENVIRONMENT'] = 'production'
        
        # Ensure logs directory exists
        log_dir = project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        print("🚀 Starting HomeGrubHub Production Server")
        print("=========================================")
        print(f"Server: http://127.0.0.1:8050")
        print("Press Ctrl+C to stop")
        print("")
        
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
        print("\n👋 Server stopped by user")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install: python -m pip install waitress")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    start_production_server()
