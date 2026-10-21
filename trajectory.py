import pandas as pd
import numpy as np
from typing import Dict, Any

class PostBolusTrajectoryEngine:
    def __init__(self, cgm_df: pd.DataFrame, event_df: pd.DataFrame,
                 glucose_col: str = "glucose_mmol", window_minutes: int = 180,
                 target_low: float = 3.9, target_high: float = 10.0):
        self.cgm_df = cgm_df.dropna(subset=[glucose_col, "Timestamp"]).sort_values("Timestamp").copy()
        self.event_df = event_df.dropna(subset=["Timestamp"]).sort_values("Timestamp").copy()
        self.glucose_col = glucose_col
        self.window_minutes = window_minutes
        self.target_low = target_low
        self.target_high = target_high

    def _get_glucose_state(self, g: float) -> str:
        if g < self.target_low:
            return "HYPO"
        elif g > self.target_high:
            return "HYPER"
        else:
            return "TARGET"

    def analyze_trajectories(self) -> pd.DataFrame:
        boluses = self.event_df[self.event_df["bolus_units"] > 0].copy()
        trajectories = []
        for _, b_row in boluses.iterrows():
            t_bolus = b_row["Timestamp"]
            units = b_row["bolus_units"]
            carbs = b_row.get("carbs_g", 0.0)
            iob = b_row.get("active_insulin_u", np.nan)

            t_end = t_bolus + pd.Timedelta(minutes=self.window_minutes)

            # isolates data 10 minutes before bolus and "window_minutes"(180) after
            window_cgm = self.cgm_df[
                (self.cgm_df["Timestamp"] >= t_bolus - pd.Timedelta(minutes=10))
                & (self.cgm_df["Timestamp"] <= t_end)
            ].copy()

            if window_cgm.empty:
                continue

            # normalizes time
            window_cgm["minutes_post"] = (
                (window_cgm["Timestamp"] - t_bolus).dt.total_seconds() / 60
            )

            baseline_candidates = window_cgm[
                (window_cgm["minutes_post"] >= -10) & (window_cgm["minutes_post"] <= 5)
            ]

            if baseline_candidates.empty:
                continue

            # finds sensor reading closest to bolus
            nearest_idx = (baseline_candidates["minutes_post"].abs()).idxmin()
            g_baseline = baseline_candidates.loc[nearest_idx, self.glucose_col]

            post_cgm = window_cgm[
                (window_cgm["minutes_post"] >=  0) & (window_cgm["minutes_post"] <= self.window_minutes)
            ]
            # at least 30 minutes of data(6 sensor readings)
            if len(post_cgm) < 6:
                continue

            min_g = post_cgm[self.glucose_col].min()
            max_g = post_cgm[self.glucose_col].max()
            max_t_idx = post_cgm[self.glucose_col].idxmax()
            t_peak = post_cgm.loc[max_t_idx, "minutes_post"]

            g_180 = (float)(np.interp(180, post_cgm["minutes_post"], post_cgm[self.glucose_col]))
            delta_180 = g_180 - g_baseline

            start_state = self._get_glucose_state(g_baseline)
            end_state = self._get_glucose_state(g_180)

            def state_transition_logic(min_g, max_g, start_state, end_state) -> tuple[str, float]:
                outcome = ""
                adverse_impact = 0.0
                if min_g < self.target_low:
                    outcome = "HYPOGLYCEMIA_RISK"
                    adverse_impact = round(self.target_low - min_g, 2)
                elif start_state == "TARGET" and end_state == "HYPER":
                    outcome = "UNDER_BOLUS_HIGH"
                    adverse_impact = round(max_g - g_baseline, 2)
                elif start_state == "HYPER" and end_state == "HYPER" and delta_180 >= 0:
                    outcome = "PERSISTENT_UNCONTROLLED_HIGH"
                    adverse_impact = round(max_g - g_baseline, 2)
                elif start_state == "TARGET" and max_g > self.target_high and end_state == "TARGET":
                    outcome = "TIMING_MISMATCH_SPIKE"
                    adverse_impact = round(max_g - g_baseline, 2)
                elif start_state == "HYPER" and end_state == "TARGET":
                    outcome = "SUCCESSFUL_CORRECTION"
                    adverse_impact = 0.0
                elif start_state == "HYPER" and end_state == "HYPER" and delta_180 < 0:
                    outcome = "PARTIAL_CORRECTION"
                    adverse_impact = 0.0
                else:
                    outcome = "ON_TARGET"
                    adverse_impact = 0.0
                return (outcome, adverse_impact)
            outcome, impact = state_transition_logic(min_g, max_g, start_state, end_state)
            trajectories.append({
                "timestamp": t_bolus,
                "day_name": t_bolus.day_name(),
                "time_str": t_bolus.strftime("%H:%M"),
                "hour": t_bolus.hour,
                "bolus_units": units,
                "carbs_g": carbs,
                "g_baseline": round(g_baseline, 2),
                "start_state": start_state,
                "min_g": round(min_g, 2),
                "max_g": round(max_g, 2),
                "g_180": round(g_180, 2),
                "end_state": end_state,
                "delta_180m": round(delta_180, 2),
                "outcome": outcome,
                "adverse_impact": impact,
            })
        return pd.DataFrame(trajectories)


    def get_outcome_summary(self) -> Dict[str, Any]:
        df_traj = self.analyze_trajectories()
        if df_traj.empty:
            return {"total_evaluated": 0}

        total = len(df_traj)
        counts = df_traj["outcome"].value_counts().to_dict()

        def pct(key: str) -> float:
            return round(counts.get(key, 0) / total * 100, 1)

        return {
            "total_evaluated": total,
            "on_target_pct": pct("ON_TARGET"),
            "hypo_risk_pct": pct("HYPOGLYCEMIA_RISK"),
            "under_bolus_pct": pct("UNDER_BOLUS_HIGH"),
            "timing_mismatch_pct": pct("TIMING_MISMATCH_SPIKE"),
            "successful_correction_pct": pct("SUCCESSFUL_CORRECTION"),
            "partial_correction_pct": pct("PARTIAL_CORRECTION"),
            "persistent_high_pct": pct("PERSISTENT_UNCONTROLLED_HIGH"),
            "counts": counts,
        }


    def get_adverse_trajectories_by_category(self, top_n: int = 3) -> Dict[str, Dict[str, Any]]:
        df_traj = self.analyze_trajectories()
        if df_traj.empty:
            return {}

        results = {}
        categories = [
            "HYPOGLYCEMIA_RISK",
            "UNDER_BOLUS_HIGH",
            "PERSISTENT_UNCONTROLLED_HIGH",
            "TIMING_MISMATCH_SPIKE",
            "SUCCESSFUL_CORRECTION",
            "PARTIAL_CORRECTION",
            "ON_TARGET",
        ]

        def categorize_part_of_day(hour: int) -> str:
            if 0 <= hour < 6:
                return "Overnight (00:00 - 06:00)"
            elif 6 <= hour < 12:
                return "Morning (06:00 - 12:00)"
            elif 12 <= hour < 18:
                return "Afternoon (12:00 - 18:00)"
            else:
                return "Evening / Late Night (18:00 - 24:00)"

        for cat in categories:
            sub = df_traj[df_traj["outcome"] == cat].copy()
            if sub.empty:
                continue

            sub["part_of_day"] = sub["hour"].apply(categorize_part_of_day)
            peak_part_of_day = sub["part_of_day"].mode().iloc[0] if not sub.empty else "N/A"

            # hourly distribution and peak hours calculation
            hourly_dist = sub["hour"].value_counts().sort_index().to_dict()
            hourly_counts_series = sub["hour"].value_counts()
            max_freq = hourly_counts_series.max()
            peak_hours = hourly_counts_series[hourly_counts_series == max_freq].index.tolist()
            peak_hours_formatted = [f"{h:02d}:00" for h in peak_hours]

            # day of week distribution and peak days
            day_dist = sub["day_name"].value_counts().to_dict()
            peak_days = sub["day_name"].mode().tolist()

            # impact sorting logic
            # sorts by lowest glucose, depth impact
            if cat == "HYPOGLYCEMIA_RISK":
                sub_sorted = sub.sort_values(by=["min_g", "adverse_impact"], ascending=[True, False])
            # categories where glucose remained high/spiked above 10.0
            # sorts based of largest impact, maximum glucose
            elif cat in ["UNDER_BOLUS_HIGH", "PERSISTENT_UNCONTROLLED_HIGH", "TIMING_MISMATCH_SPIKE"]:
                sub_sorted = sub.sort_values(by=["adverse_impact", "max_g"], ascending=[False, False])
            # successful correction, partial correction, on target
            # highlights by the most effective corrections
            else:
                sub_sorted = sub.sort_values(by="delta_180m", ascending=True)

            critical_events = sub_sorted.head(top_n).to_dict(orient="records")

            results[cat] = {
                "total_count": len(sub),
                "peak_part_of_day": peak_part_of_day,
                "peak_hours": peak_hours_formatted,
                "hourly_distribution": hourly_dist,
                "peak_days": peak_days,
                "day_distribution": day_dist,
                "critical_events": critical_events,
            }

        return results