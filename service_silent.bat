@echo off
setlocal enabledelayedexpansion

REM Celtic Language Platform - Silent Service Control
REM =================================================

set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%production_server.py
set LOG_DIR=%SCRIPT_DIR%logs

:: Ensure logs directory exists
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Command dispatch
if "%1"=="start"   goto start
if "%1"=="stop"    goto stop
if "%1"=="restart" goto restart
if "%1"=="status"  goto status
if "%1"=="logs"    goto logs

:help
echo.
echo HomeGrubHub Platform - Silent Service Control
echo =================================================
echo.
echo Usage: service_silent.bat [start^|stop^|restart^|status^|logs]
echo.
echo Commands:
echo   start    - Start server silently (no console window)
echo   stop     - Stop the server by port
echo   restart  - Restart the server
echo   status   - Check if the server is running
echo   logs     - Show recent production log lines
echo.
goto end

:start
echo Starting HomeGrubHub Platform silently...
powershell -WindowStyle Hidden -Command ^
"Start-Process python -ArgumentList '\"%PYTHON_SCRIPT%\" --silent' -WindowStyle Hidden"
timeout /t 2 /nobreak >nul
goto status

:stop
echo Stopping HomeGrubHub Platform...
set "found=0"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8050" ^| findstr "LISTENING"') do (
    set "found=1"
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! == 0 (
        echo ✅ Server stopped successfully (PID %%a)
    ) else (
        echo ⚠️ Failed to stop process (PID %%a)
    )
)
if "!found!"=="0" (
    echo ⚠️ No process found listening on port 8050.
)
goto end

:restart
echo Restarting HomeGrubHub Platform...
call :stop
timeout /t 2 /nobreak >nul
call :start
goto end

:status
echo Checking server status...
netstat -an | findstr ":8050" | findstr "LISTENING" >nul
if %errorlevel%==0 (
    echo ✅ Server is running silently on port 8050
    echo 🌐 Access via: http://127.0.0.1:8050
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8004" ^| findstr "LISTENING"') do (
        echo 📊 Process ID: %%a
    )
) else (
    echo ❌ Server is not running
    echo 💡 Use 'service_silent.bat start' to launch the server
)
goto end

:logs
echo.
echo Recent production logs:
echo ========================
if exist "%LOG_DIR%\production.log" (
    powershell "Get-Content '%LOG_DIR%\production.log' -Tail 20"
) else (
    echo ⚠️ No production log found.
    echo ℹ️  The server may not have started or hasn't written logs yet.
)
goto end

:end
endlocal
