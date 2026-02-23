@echo off
setlocal

echo ==========================================
echo   Production Line Scheduler - Launcher
echo ==========================================
echo.

REM --- Check prerequisites ---

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Install Python 3.11+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo         Install Node.js 20+ from https://nodejs.org
    pause
    exit /b 1
)

REM --- Backend setup ---

if not exist "backend\.venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    python -m venv backend\.venv
) else (
    echo [1/4] Virtual environment already exists.
)

echo [2/4] Installing backend dependencies...
call backend\.venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
)

REM --- Frontend setup & build ---

echo [3/4] Installing frontend dependencies...
cd frontend
call npm install --silent
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies.
    cd ..
    pause
    exit /b 1
)

echo [4/4] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed.
    cd ..
    pause
    exit /b 1
)
cd ..

REM --- Launch ---

echo.
echo ==========================================
echo   Starting server on http://localhost:8000
echo   Press Ctrl+C to stop.
echo ==========================================
echo.

start http://localhost:8000

cd backend
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
