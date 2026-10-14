import pandas as pd

class MetricsCalculator:
    def __init__(self, cgm_df: pd.DataFrame, glucose_col: str = "glucose_mmol"):
        self.cgm_df = cgm_df.dropna(subset=[glucose_col])
        self.glucose = self.cgm_df[glucose_col]

    def calculate_metrics(self):
        if self.glucose.empty:
            return {}

        total_readings = len(self.glucose)
        mean_mmol = self.glucose.mean()
        sd_mmol = self.glucose.std()

        #coefficient of variation
        cv_pct = (sd_mmol / mean_mmol) * 100 if mean_mmol > 0 else 0.0

        # glucose management indicator (gmi)
        # https://pmc.ncbi.nlm.nih.gov/articles/PMC6196826/
        # 1 mmol / L ≈ 18.0156 mg/dL
        gmi_pct = 3.31 + (0.43093 * mean_mmol)

        very_low_pct = (self.glucose < 3.0).sum() / total_readings * 100
        low_pct = ((self.glucose >= 3.0) & (self.glucose < 3.9)).sum() / total_readings * 100
        target_tir_pct = ((self.glucose >= 3.9) & (self.glucose <= 10.0)).sum() / total_readings * 100
        high_pct = ((self.glucose > 10.0) & (self.glucose <= 13.9)).sum() / total_readings * 100
        very_high_pct = (self.glucose > 13.9).sum() / total_readings * 100

        return {
            "total_readings": total_readings,
            "mean_glucose_mmol": round(mean_mmol, 2),
            "sd_mmol": round(sd_mmol, 2),
            "cv_percent": round(cv_pct, 1),
            "gmi_percent": round(gmi_pct, 2),
            "tir_very_low_pct": round(very_low_pct, 1),
            "tir_low_pct": round(low_pct, 1),
            "tir_target_pct": round(target_tir_pct, 1),
            "tir_high_pct": round(high_pct, 1),
            "tir_very_high_pct": round(very_high_pct, 1),
        }

    def print_clinical_report(self) -> None:
        metrics = self.calculate_metrics()
        if not metrics:
            print("No CGM readings available for metric calculation.")
            return

        print("==========================================")
        print("     CLINICAL CGM SUMMARY REPORT          ")
        print("==========================================")
        print(f"Total CGM Readings Evaluated : {metrics['total_readings']}")
        print(f"Mean Sensor Glucose          : {metrics['mean_glucose_mmol']} mmol/L")
        print(f"Standard Deviation (SD)      : {metrics['sd_mmol']} mmol/L")
        print(f"Glycemic Variability (%CV)   : {metrics['cv_percent']}% "
              f"({'Target Met <=36%' if metrics['cv_percent'] <= 36 else 'High Variability >36%'})")
        print(f"Glucose Management Indicator : {metrics['gmi_percent']}% (Est. HbA1c)")
        print("\n--- Time In Range (TIR) Breakdown ---")
        print(f"  Very High (>13.9 mmol/L)   : {metrics['tir_very_high_pct']}%")
        print(f"  High (10.1 - 13.9 mmol/L)  : {metrics['tir_high_pct']}%")
        print(f"  Target (3.9 - 10.0 mmol/L) : {metrics['tir_target_pct']}%")
        print(f"  Low (3.0 - 3.8 mmol/L)     : {metrics['tir_low_pct']}%")
        print(f"  Very Low (<3.0 mmol/L)     : {metrics['tir_very_low_pct']}%")
        print("==========================================")
