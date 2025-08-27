# HomeGrubHub PWrite-Host "Starting Waitress server..." -ForegroundColor Cyan
Write-Host "Server will be available at: http://127.0.0.1:8050" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    # Start the application with Waitress (Windows-compatible)
    python run_production.pyn Startup Script (PowerShell)

Write-Host "Starting HomeGrubHub in Production Mode..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Check if logs directory exists
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs"
    Write-Host "Created logs directory" -ForegroundColor Yellow
}

# Set production environment variables
$env:FLASK_ENV = "production"
$env:ENVIRONMENT = "production"

Write-Host "Starting Gunicorn server..." -ForegroundColor Cyan
Write-Host "Server will be available at: http://127.0.0.1:8050" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    # Start the application with Gunicorn
    python -m gunicorn -c gunicorn.conf.py wsgi:application
}
catch {
    Write-Host "Error starting server: $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "Server stopped." -ForegroundColor Yellow
}
