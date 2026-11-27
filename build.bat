@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv311\Scripts\python.exe" (
    echo [1/3] Creating Python 3.11 virtual environment...
    py -3.11 -m venv .venv311
    if errorlevel 1 (
        echo ERROR: Python 3.11 not found. Install Python 3.11 first.
        pause
        exit /b 1
    )
    ".venv311\Scripts\python.exe" -m pip install --upgrade pip
    ".venv311\Scripts\python.exe" -m pip install -r requirements.txt
    ".venv311\Scripts\python.exe" -m pip install -e . --no-deps
)

echo [2/3] Running pytest verification...
".venv311\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo ERROR: Tests failed.
    pause
    exit /b 1
)

echo [3/3] Compiling OptimasiWindows.exe with Nuitka (Python 3.11)...
".venv311\Scripts\python.exe" build_nuitka.py %*
if errorlevel 1 (
    echo ERROR: Nuitka build failed.
    pause
    exit /b 1
)

echo.
echo Build succeeded! Output: dist\OptimasiWindows.exe
pause
