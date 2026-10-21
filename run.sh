#!/bin/bash
cd "$(dirname "$0")"

# Check if virtual environment exists; if not, create it and install packages
if [ ! -d ".venv" ]; then
    echo "First-time setup detected. Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install pandas numpy plotly streamlit pytest
else
    source .venv/bin/activate
fi

# Launch Streamlit application
python3 -m streamlit run app.py