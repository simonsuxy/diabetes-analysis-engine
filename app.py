import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Make sure these import names match your actual filenames
from ingest import Ingestor
from metrics import MetricsCalculator
from patterns import PatternAnalyzer
from trajectory import PostBolusTrajectoryEngine

# --- STREAMLIT PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Diabetes Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
    <style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef; }
    </style>
""", unsafe_allow_html=True)

st.title("CareLink Diabetes Analytics Dashboard")
st.caption("Modular Time-Series Analytics & Post-Bolus Trajectory Engine")

# --- SIDEBAR: DATA INGESTION ---
st.sidebar.header("📁 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload CareLink CSV Export", type=["csv"])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Target Range Configuration")
target_low = st.sidebar.number_input("Hypo Threshold (mmol/L)", value=3.9, step=0.1)
target_high = st.sidebar.number_input("Hyper Threshold (mmol/L)", value=10.0, step=0.1)

if uploaded_file is not None:
    try:
        # Pass the uploaded string content directly to the Ingestor
        csv_string = uploaded_file.getvalue().decode("utf-8-sig")
        ingestor = Ingestor(csv_content=csv_string)
    except Exception as e:
        st.error(f"Error parsing uploaded CareLink file: {e}")
        st.stop()

    st.sidebar.success(
        f"Loaded **{len(ingestor.cgm_data):,}** CGM readings and **{len(ingestor.event_data):,}** pump events.")

    # Initialize Engine Components using the sidebar targets
    calculator = MetricsCalculator(
        cgm_df=ingestor.cgm_data,
        target_low=target_low,
        target_high=target_high
    )
    analyzer = PatternAnalyzer(
        cgm_df=ingestor.cgm_data,
        target_low=target_low,
        target_high=target_high
    )
    engine = PostBolusTrajectoryEngine(
        cgm_df=ingestor.cgm_data,
        event_df=ingestor.event_data,
        target_low=target_low,
        target_high=target_high
    )

    # Fetch results using your updated method names
    metrics = calculator.calculate_metrics()
    summary = engine.get_outcome_summary()

    # --- TOP EXECUTIVE METRIC CARDS ---
    st.subheader("📊 Executive Clinical Summary")
    col1, col2, col3, col4, col5 = st.columns(5)

    # Safely retrieve values using the new keys defined in MetricsCalculator
    tir_val = metrics.get('tir_target_pct', 0.0)
    cv_val = metrics.get('cv_percent', 0.0)
    gmi_val = metrics.get('gmi_percent', 0.0)
    mean_val = metrics.get('mean_glucose_mmol', 0.0)

    # Hypo time is the sum of low and very low (<3.0)
    hypo_val = round(metrics.get('tir_low_pct', 0.0) + metrics.get('tir_very_low_pct', 0.0), 1)

    col1.metric("Time in Range (TIR)", f"{tir_val}%", delta="Target > 70%" if tir_val >= 70 else "Below Target")
    col2.metric("Glycemic Var (%CV)", f"{cv_val}%", delta="Stable <= 36%" if cv_val <= 36 else "High Volatility",
                delta_color="inverse")
    col3.metric("Est. HbA1c (GMI)", f"{gmi_val}%")
    col4.metric("Mean Glucose", f"{mean_val} mmol/L")
    col5.metric("Hypo Time", f"{hypo_val}%", delta="Target < 4%", delta_color="inverse")

    st.markdown("---")

    # --- DASHBOARD TABS LAYOUT ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 24h AGP Profile",
        "⚠️ Pattern & Risk Alerts",
        "🎯 Post-Bolus Trajectories",
        "📄 Raw Ingested Data"
    ])

    # ==========================================
    # TAB 1: 24-HOUR AGP MODAL DAY PROFILE
    # ==========================================
    with tab1:
        st.subheader("24-Hour Ambulatory Glucose Profile (AGP)")
        cgm_df = ingestor.cgm_data.copy()
        cgm_df["hour"] = cgm_df["Timestamp"].dt.hour

        hourly_stats = cgm_df.groupby("hour")["glucose_mmol"].agg(
            p25=lambda x: x.quantile(0.25),
            p50="median",
            p75=lambda x: x.quantile(0.75)
        ).reset_index()

        fig_agp = go.Figure()

        # Target Range Highlight Box
        fig_agp.add_hrect(
            y0=target_low, y1=target_high,
            fillcolor="rgba(76, 175, 80, 0.12)", line_width=0,
            annotation_text="Target Range", annotation_position="top left"
        )

        # 25th - 75th Percentile Band
        fig_agp.add_trace(go.Scatter(
            x=hourly_stats["hour"], y=hourly_stats["p75"],
            mode="lines", name="75th Percentile", line=dict(width=0), showlegend=False
        ))
        fig_agp.add_trace(go.Scatter(
            x=hourly_stats["hour"], y=hourly_stats["p25"],
            mode="lines", name="25th-75th Percentile Range",
            fill='tonexty', fillcolor='rgba(33, 150, 243, 0.2)', line=dict(width=0)
        ))

        # Median Line
        fig_agp.add_trace(go.Scatter(
            x=hourly_stats["hour"], y=hourly_stats["p50"],
            mode="lines+markers", name="Median Glucose", line=dict(color="#1e88e5", width=3)
        ))

        fig_agp.update_layout(
            xaxis=dict(title="Hour of Day", dtick=2, range=[0, 23]),
            yaxis=dict(title="Glucose (mmol/L)", range=[2, 22]),
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_agp, use_container_width=True)

    # ==========================================
    # TAB 2: RECURRING PATTERN & HOUR ALERTS
    # ==========================================
    with tab2:
        st.subheader("Recurring Day/Hour Glycemic Patterns")
        pattern_alerts = analyzer.detect_specific_patterns()

        if pattern_alerts:
            alerts_df = pd.DataFrame(pattern_alerts)
            st.dataframe(
                # Updated keys mapped to match PatternAnalyzer logic
                alerts_df[["alert_type", "day_name", "hour_window", "details"]],
                use_container_width=True,
                column_config={
                    "alert_type": st.column_config.TextColumn("Alert Type"),
                    "day_name": st.column_config.TextColumn("Day of Week"),
                    "hour_window": st.column_config.TextColumn("Time Window"),
                    "details": st.column_config.TextColumn("Pattern Diagnostic Details"),
                }
            )
        else:
            st.info("No recurring hourly pattern alerts detected across the dataset.")

        # Day of Week Comparison Table
        st.subheader("Day-of-Week Glycemic Stability Summary")
        daily_summary = analyzer.compute_daily_summary()
        st.dataframe(daily_summary, use_container_width=True)

    # ==========================================
    # TAB 3: POST-BOLUS TRAJECTORY ANALYZER
    # ==========================================
    with tab3:
        st.subheader("Post-Bolus Trajectory Engine")

        tcol1, tcol2, tcol3, tcol4 = st.columns(4)
        tcol1.metric("Evaluated Doses", summary.get('total_evaluated', 0))
        tcol2.metric("On-Target Control", f"{summary.get('on_target_pct', 0)}%")
        tcol3.metric("Hypo Risk", f"{summary.get('hypo_risk_pct', 0)}%", delta_color="inverse")
        tcol4.metric("Under-Bolus High", f"{summary.get('under_bolus_pct', 0)}%", delta_color="inverse")

        st.markdown("---")

        cat_data = engine.get_adverse_trajectories_by_category(top_n=5)

        if cat_data:
            selected_cat = st.selectbox("Select Outcome Category to Drill Down", list(cat_data.keys()))

            if selected_cat and selected_cat in cat_data:
                details = cat_data[selected_cat]

                st.info(
                    f"**Category:** {selected_cat} | "
                    f"**Total Events:** {details['total_count']} | "
                    f"**Peak Window:** {details['peak_part_of_day']} ({', '.join(details['peak_hours'])}) | "
                    f"**Peak Day(s):** {', '.join(details['peak_days'])}"
                )

                st.write("##### Critical Impact Boluses (Ranked by Severity)")
                crit_df = pd.DataFrame(details["critical_events"])

                if not crit_df.empty:
                    st.dataframe(
                        crit_df[[
                            "day_name", "time_str", "bolus_units", "carbs_g",
                            "g_baseline", "start_state", "min_g", "max_g", "g_180", "end_state", "adverse_impact"
                        ]],
                        use_container_width=True,
                        column_config={
                            "day_name": "Day",
                            "time_str": "Time",
                            "bolus_units": "Dose (U)",
                            "carbs_g": "Carbs (g)",
                            "g_baseline": "Start Glucose",
                            "start_state": "Start State",
                            "min_g": "Min Glucose",
                            "max_g": "Peak Glucose",
                            "g_180": "+180m Glucose",
                            "end_state": "Final State",
                            "adverse_impact": "Impact Score"
                        }
                    )
        else:
            st.info("No trajectories available for analysis.")

    # ==========================================
    # TAB 4: RAW INGESTED DATA PREVIEW
    # ==========================================
    with tab4:
        st.subheader("Ingested Data Preview")
        rcol1, rcol2 = st.columns(2)
        with rcol1:
            st.write("##### CGM Sensor Stream")
            st.dataframe(ingestor.cgm_data.head(100), use_container_width=True)
        with rcol2:
            st.write("##### Pump Event Stream")
            st.dataframe(ingestor.event_data.head(100), use_container_width=True)

else:
    st.info("👈 Please upload a Medtronic CareLink CSV export file (`.csv`) in the sidebar to run the engine.")