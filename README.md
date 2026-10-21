# Diabetes Analysis Engine

A modular time-series analytics and post-bolus trajectory engine built in Python to parse Continuous Glucose Monitor (CGM) and insulin pump exports, evaluate standard clinical health metrics, detect recurring hourly patterns, and analyze post-prandial outcomes.

---

## Architecture & Modules

- **Advanced Ingestion (`ingest.py`):** Multi-section Medtronic CareLink parser via the `Ingestor` class that handles structured metadata, European comma-to-dot decimal format conversions, timestamp normalization, and dedicated CGM (`cgm_data`) and event stream (`event_data`) extractions.
- **Clinical Metrics Engine (`metrics.py`):** Computes gold-standard metrics including **Time in Range (TIR)**, Glycemic Variability (**%CV**), Glucose Management Indicator (**GMI** / Estimated HbA1c), and time below/above range thresholds.
- **Recurring Pattern Analyzer (`patterns.py`):** Slices 24-hour daily windows and day-of-week profiles to detect recurring hypo/hyperglycemic risk windows.
- **Post-Bolus Trajectory Engine (`trajectory.py`):** The `PostBolusTrajectoryEngine` indexes 180-minute post-prandial glucose curves relative to insulin boluses. It calculates baseline states, glucose peaks/troughs, 180-minute deltas, and categorizes outcomes (e.g., `HYPOGLYCEMIA_RISK`, `TIMING_MISMATCH_SPIKE`, `UNDER_BOLUS_HIGH`, or `SUCCESSFUL_CORRECTION`) complete with stratified part-of-day metrics, peak hours, day-of-week distributions, and critical event summaries.
- **Interactive Dashboard (`app.py`):** Streamlit web interface featuring executive KPI scorecards, 24-hour Ambulatory Glucose Profile (AGP) charts, and interactive drill-down tables.

---

## Installation & First-Time Setup

No manual dependency installation is required. The provided startup scripts automatically create a local virtual environment, install requirements from `requirements.txt`, and launch the dashboard on the first run.

### Windows (`run.bat`)

1. Double-click `run.bat` (or execute it via Command Prompt).
2. The script will automatically create `.venv`, install packages on first run, and start the app.

### Linux / macOS (`run.sh`)

1. Grant execution permissions once:
   ```bash
   chmod +x run.sh
   ```
2. Execute the script:
   ```bash
   ./run.sh
   ```

---

## Requirements

The project dependencies are listed in `requirements.txt`:
```text
pandas
numpy
plotly
streamlit
pytest
```

---

## License

This project is open-source and available under the [MIT License](LICENSE).