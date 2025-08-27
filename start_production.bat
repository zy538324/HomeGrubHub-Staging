@echo off
REM HomeGrubHub Production Startup Script

echo Starting HomeGrubHub in Production Mode...
echo ========================================

REM Check if logs directory exists
if not exist "logs" mkdir logs

REM Set production environment variables
set FLASK_ENV=production
set ENVIRONMENT=production

REM Start the application with Waitress (Windows-compatible)
echo Starting Waitress server...
echo Server will be available at: http://127.0.0.1:8050
echo Press Ctrl+C to stop the server
echo.

python run_production.py

echo.
echo Server stopped.
pause
