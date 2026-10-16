from typing import Dict, Any

import pandas as pd

class PatternAnalyzer:
    def __init__(self, cgm_df: pd.DataFrame, glucose_col: str = "glucose_mmol"):
        self.df = cgm_df.dropna(subset=[glucose_col, "Timestamp"]).copy()
        self.glucose_col = glucose_col
        self.df["hour"] = self.df["Timestamp"].dt.hour
        self.df["day_name"] = self.df["Timestamp"].dt.day_name()

    def compute_hourly_summary(self) -> pd.DataFrame:
        hourly_records = []
        for hour in range(24):
            sub = self.df[self.df["hour"] == hour][self.glucose_col]
            if sub.empty:
                continue

            count = len(sub)
            mean_mmol = sub.mean()
            std_mmol = sub.std()

            hypo_pct = (sub < 3.9).sum() / count * 100
            severe_hypo_pct = (sub < 3.0).sum() / count * 100
            target_pct = ((sub >= 3.9) & (sub <= 10.0)).sum() / count * 100
            hyper_pct = (sub > 10.0).sum() / count * 100

            hourly_records.append({
                "hour": hour,
                "hour_window": f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00",
                "readings_count": count,
                "mean_mmol": round(mean_mmol, 2),
                "sd_mmol": round(std_mmol, 2),
                "median_mmol": round(sub.median(), 2),
                "hypo_pct": round(hypo_pct, 1),
                "severe_hypo_pct": round(severe_hypo_pct, 1),
                "target_pct": round(target_pct, 1),
                "hyper_pct": round(hyper_pct, 1),
            })
        return pd.DataFrame(hourly_records)

    def compute_daily_summary(self) -> pd.DataFrame:
        days = ["Monday", "Tuesday", "Wednesday","Thursday","Friday","Saturday","Sunday"]
        daily_records = []

        for day in days:
            sub = self.df[self.df["day_name"] == day][self.glucose_col]
            if sub.empty:
                continue
            count = len(sub)
            mean_mmol = sub.mean()
            std_mmol = sub.std()
            cv_pct = (std_mmol / mean_mmol) * 100 if mean_mmol > 0 else 0.0
            hypo_pct = (sub < 3.9).sum() / count * 100
            severe_hypo_pct = (sub < 3.0).sum() / count * 100
            target_pct = ((sub >= 3.9) & (sub <= 10.0)).sum() / count * 100
            hyper_pct = (sub > 10.0).sum() / count * 100

            daily_records.append({
                "day_name": day,
                "readings_count": count,
                "mean_mmol": round(mean_mmol, 2),
                "sd_mmol": round(std_mmol, 2),
                "cv_percent": round(cv_pct, 1),
                "hypo_pct": round(hypo_pct, 1),
                "severe_hypo_pct": round(severe_hypo_pct, 1),
                "target_pct": round(target_pct, 1),
                "hyper_pct": round(hyper_pct, 1)
            })
        return pd.DataFrame(daily_records)

    def detect_specific_patters(self,
                                hypo_threshold_pct: float = 25.0, hyper_threshold_pct: float = 60.0
                                ) -> list[Dict[str, Any]]:
        hourly_summary = self.df.groupby(["day_name", "hour"])[self.glucose_col].agg(
            count="count",
            hypo_pct=lambda x: (x < 3.9).sum() / len(x) * 100,
            hyper_pct=lambda x: (x > 10.0).sum() / len(x) * 100,
        ).reset_index()

        alerts = []
        for row in hourly_summary.itertuples():
            h_str = f"{row.hour:02d}:00 - {(row.hour + 1) % 24:02d}:00"
            if row.hypo_pct >= hypo_threshold_pct:
                alerts.append({
                    "day_name": row.day_name,
                    "hour_window": h_str,
                    "alert_type": "SPECIFIC_DAY_HYPO_RISK",
                    "details": f"{row.day_name}s at {h_str}: {round(row.hypo_pct, 1)}% of readings < 3.9 mmol/L"
                })
            elif row.hyper_pct >= hyper_threshold_pct:
                alerts.append({
                    "day_name": row.day_name,
                    "hour_window": h_str,
                    "alert_type": "SPECIFIC_DAY_HYPER_PATTERN",
                    "details": f"{row.day_name}s at {h_str}: {round(row.hyper_pct, 1)}% of readings > 10.0 mmol/L",
                })
        return alerts