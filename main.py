from ingest import Ingestor
from metrics import MetricsCalculator
from patterns import PatternAnalyzer
from trajectory import PostBolusTrajectoryEngine

if __name__ == "__main__":
    filepath = r"C:\Users\ninja\Documents\code\diabetes-analysis\data\test.csv"
    ingestor = Ingestor(filepath = filepath)
    calculator = MetricsCalculator(cgm_df=ingestor.cgm_data)
    calculator.print_clinical_report()

    analyzer = PatternAnalyzer(cgm_df=ingestor.cgm_data)

    print("\n--- Day of Week Glycemic Profile ---")
    print(analyzer.compute_daily_summary())

    # General 24-hour hourly alerts
    hourly_alerts = analyzer.detect_specific_patters()

    if hourly_alerts:
        print(f"Found {len(hourly_alerts)} recurring pattern alerts:\n")
        for alert in hourly_alerts:
            print(f"{alert['day_name']} {alert['hour_window']} -> {alert['details']}")
    else:
        print("No severe recurring pattern alerts detected.")

# Post-Bolus Trajectory Engine
    print("\n==========================================")
    print("   POST-BOLUS TRAJECTORY ENGINE  ")
    print("==========================================")
    engine = PostBolusTrajectoryEngine(
        cgm_df=ingestor.cgm_data,
        event_df=ingestor.event_data
    )

    summary = engine.get_outcome_summary()
    print(f"Total Bolus Trajectories Evaluated : {summary['total_evaluated']}")
    print(f"  - On Target Control             : {summary.get('on_target_pct', 0)}%")
    print(f"  - Post-Bolus Hypo Risk          : {summary.get('hypo_risk_pct', 0)}%")
    print(f"  - Under-Bolus Persistent High   : {summary.get('under_bolus_pct', 0)}%")
    print(f"  - Timing Mismatch (Early Spike) : {summary.get('timing_mismatch_pct', 0)}%")
    print(f"  - Successful Correction Drop    : {summary.get('successful_correction_pct', 0)}%")
    print(f"  - Partial Correction Drop       : {summary.get('partial_correction_pct', 0)}%")
    print(f"  - Persistent High (Unchanged)   : {summary.get('persistent_high_pct', 0)}%")

    print("\n----------------------------------------------------------------------")
    print("   TIME DISTRIBUTION & CRITICAL IMPACT ANALYSIS BY OUTCOME CATEGORY   ")
    print("----------------------------------------------------------------------")
    category_data = engine.get_adverse_trajectories_by_category(top_n=3)

    for cat_name, details in category_data.items():
        print(f"\n>>> Category: {cat_name} (Total: {details['total_count']} events)")
        print(f"    • Peak Part of Day : {details['peak_part_of_day']}")
        print(f"    • Peak Hour(s)     : {', '.join(details['peak_hours'])}")
        print(f"    • Hourly Map       : {details['hourly_distribution']}")
        print(f"    • Top Day(s)       : {', '.join(details['peak_days'])}")
        print(f"    • Daily Map        : {details['day_distribution']}")
        print("    • Top Critical Impact Boluses:")

        for ev in details["critical_events"]:
            print(f"      - [{ev['day_name']} at {ev['time_str']}] Dose: {ev['bolus_units']}U | Carbs: {ev['carbs_g']}g")
            print(f"        Transition: Baseline {ev['g_baseline']} mmol/L ({ev['start_state']}) -> 180m: {ev['g_180']} mmol/L ({ev['end_state']})")
            print(f"        Window Extremes: Min = {ev['min_g']} mmol/L, Max = {ev['max_g']} mmol/L")