@echo off
cd /d "%~dp0"

:: Check if virtual environment exists; if not, create it and install packages
if not exist .venv (
    echo First-time setup detected. Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install pandas numpy plotly streamlit pytest
) else (
    call .venv\Scripts\activate.bat
)

:: Launch Streamlit application
python -m streamlit run app.py

pause