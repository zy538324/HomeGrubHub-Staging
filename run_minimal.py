"""
Minimal run script to test app startup
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("🚀 Starting minimal Flask app...")
    
    from run import app
    print("✅ App imported successfully")
    
    # Test app configuration
    with app.app_context():
        print(f"✅ App context works")
        print(f"   Debug mode: {app.debug}")
        print(f"   Secret key configured: {bool(app.config.get('SECRET_KEY'))}")
        print(f"   Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")
    
    print("🌐 Starting Flask development server...")
    print("   Access the app at: http://127.0.0.1:8050")
    print("   Press Ctrl+C to stop")
    print("=" * 50)
    
    # Start the app with minimal options
    app.run(
        host='127.0.0.1',
        port=8050,
        debug=False,  # Disable debug to avoid reloader issues
        use_reloader=False,  # Disable auto-reload
        threaded=True
    )
    
except KeyboardInterrupt:
    print("\n👋 Server stopped by user")
except Exception as e:
    print(f"❌ Error starting app: {e}")
    import traceback
    traceback.print_exc()
