import os
import sys
from recipe_app.db import create_app

app = create_app()

def run_development():
    """Run the application in development mode"""
    print("Starting HomeGrubHub in development mode...")
    print("Access the app at: http://127.0.0.1:8050")
    app.run(host='0.0.0.0', port=8050, debug=True, use_reloader=False)

def run_production():
    """Run the application in production mode"""
    print("Starting HomeGrubHub in production mode...")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8050)),
        debug=False
    )

if __name__ == "__main__":
    # Check for production environment or command line argument
    is_production = (
        os.environ.get("FLASK_ENV") == "production" or
        os.environ.get("ENVIRONMENT") == "production" or
        "--production" in sys.argv
    )
    
    if is_production:
        run_production()
    else:
        run_development()
