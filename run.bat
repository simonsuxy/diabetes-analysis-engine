@echo off
cd /d "%~dp0"

:: Check if virtual environment exists; if not, create it
if not exist .venv (
    echo First-time setup detected. Creating virtual environment...
    
    :: Try using the 'py' launcher first, otherwise fall back to 'python'
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )

    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: Launch Streamlit application
python -m streamlit run app.py

pause