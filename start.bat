@echo off
setlocal

echo ==================================================
echo   Lemihandle - Spatial Intent Engine
echo ==================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    pause
    exit /b
)

:: 2. Create Virtual Environment and Install Dependencies
if not exist "venv\" (
    echo [*] First time setup detected. Creating virtual environment...
    python -m venv venv
    
    echo [*] Activating venv and installing Backend dependencies...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r backend\requirements.txt
    
    echo [*] Installing Frontend dependencies...
    pip install -r frontend\requirements.txt
    
    echo [*] Dependencies installed successfully!
) else (
    call venv\Scripts\activate.bat
)

:: 3. Check for backend API key
if not exist "backend\.env" (
    echo [*] Creating default backend\.env file...
    echo GEMINI_API_KEYS=PUT_YOUR_API_KEY_HERE> backend\.env
    echo LEMIHANDLE_MODEL=gemini-2.5-flash-lite>> backend\.env
    echo.
    echo --------------------------------------------------
    echo  [ACTION REQUIRED]
    echo  I created a 'backend\.env' file for you.
    echo  Please open it and replace 'PUT_YOUR_API_KEY_HERE' 
    echo  with your real Google Gemini API Key.
    echo.
    echo  Then double-click start.bat again!
    echo --------------------------------------------------
    pause
    exit /b
)

:: 4. Launch Backend (in a new window so it stays alive and visible)
echo [*] Starting FastAPI AI Brain...
start "Lemihandle Backend Server" cmd /c "cd backend && title Lemihandle Backend && ..\venv\Scripts\python -m uvicorn main:app --port 8000"

:: Wait a moment for the server to bind to the port
echo [*] Waiting for backend to warm up...
timeout /t 3 /nobreak >nul

:: 5. Launch Frontend
echo [*] Starting GUI Overlay...
cd frontend
..\venv\Scripts\python main.py

endlocal
