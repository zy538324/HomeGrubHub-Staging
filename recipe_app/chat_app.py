"""
Chat Integration for Flask App
This module integrates SocketIO chat functionality into the main Flask application
"""

from flask_socketio import SocketIO

# Global SocketIO instance
socketio = None

def create_app_with_chat():
    """Create Flask app with SocketIO chat support"""
    from recipe_app.db import create_app
    
    # Create the main Flask app
    app = create_app()
    
    # Initialize SocketIO with fallback async modes
    global socketio
    try:
        # Try eventlet first
        import eventlet
        socketio = SocketIO(
            app, 
            cors_allowed_origins="*", 
            async_mode='eventlet',
            logger=True,
            engineio_logger=False
        )
        print("🔌 Using eventlet async mode")
    except (ImportError, AttributeError):
        # Fall back to threading
        socketio = SocketIO(
            app, 
            cors_allowed_origins="*", 
            async_mode='threading',
            logger=True,
            engineio_logger=False
        )
        print("🔌 Using threading async mode")
    
    # Set up chat functionality
    from recipe_app.utils.chat_support import setup_chat_socketio
    setup_chat_socketio(app)
    
    return app, socketio

def get_socketio():
    """Get the global SocketIO instance"""
    return socketio
