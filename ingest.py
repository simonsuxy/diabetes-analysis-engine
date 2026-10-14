from pathlib import Path
import pandas as pd
from io import StringIO

SECTION_CSV_MARKER = "-------"
HEADER_START = "Index;Date;Time"


def parse_section(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace("", pd.NA).copy()

    # combines date and time columns into a single "Timestamp"
    if "Date" in df.columns and "Time" in df.columns:
        df["Timestamp"] = pd.to_datetime(
            df["Date"] + " " + df["Time"],
            format="%Y/%m/%d %H:%M:%S",
            errors="coerce"
        )

    # converts ',' in numbers to '.' (ex: 3,14 => 3.14)
    for col in df.columns:
        if col in {"Index", "Date", "Time", "Timestamp"}:
            continue
        conv = pd.to_numeric(
            df[col].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )
        # apply conversion only if all non-null entries convert cleanly
        if conv.notna().sum() > 0 and conv.notna().sum() == df[col].notna().sum():
            df[col] = conv

    return df.dropna(axis=1, how="all")


def extract_cgm_stream(parsed_sections: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = parsed_sections.get("Sensor")
    if df is None or "Sensor Glucose (mmol/L)" not in df.columns:
        df = parsed_sections.get("Pump")  # Fallback

    if df is None or "Sensor Glucose (mmol/L)" not in df.columns:
        return pd.DataFrame(columns=["Timestamp", "glucose_mmol"])

    cgm = df[["Timestamp", "Sensor Glucose (mmol/L)"]].copy()
    cgm.columns = ["Timestamp", "glucose_mmol"]

    cgm["glucose_mmol"] = pd.to_numeric(cgm["glucose_mmol"], errors="coerce")

    cgm = cgm.dropna(subset=["Timestamp", "glucose_mmol"])
    cgm = cgm[cgm["glucose_mmol"] > 0]
    cgm = cgm.sort_values("Timestamp").drop_duplicates(subset=["Timestamp"], keep="last")

    return cgm.reset_index(drop=True)


def extract_events_stream(parsed_sections: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = parsed_sections.get("Pump")
    if df is None:
        return pd.DataFrame(columns=["Timestamp", "bolus_units", "carbs_g", "active_insulin_u"])

    events = df[["Timestamp"]].copy()

    events["bolus_units"] = pd.to_numeric(
        df.get("Bolus Volume Delivered (U)"), errors="coerce"
    ).fillna(0.0)

    events["carbs_g"] = pd.to_numeric(
        df.get("BWZ Carb Input (grams)"), errors="coerce"
    ).fillna(0.0)

    events["active_insulin_u"] = pd.to_numeric(
        df.get("BWZ Active Insulin (U)"), errors="coerce"
    )

    events = events.dropna(subset=["Timestamp"])
    events = events[(events["bolus_units"] > 0) | (events["carbs_g"] > 0)]

    return events.sort_values("Timestamp").reset_index(drop=True)


class Ingestor:
    def __init__(self, filepath, target_interval=5):
        self.filepath = Path(filepath)
        self.target_interval = target_interval
        self.raw_data = self._load_raw_data()
        self.parsed_data = {
            name: parse_section(df)
            for name, df in self.raw_data.items()
            if name != "metadata"
        }
        self.cgm_data = extract_cgm_stream(self.parsed_data)
        self.event_data = extract_events_stream(self.parsed_data)

    def _load_raw_data(self) -> dict[str, pd.DataFrame]:
        out = {}

        text = self.filepath.read_text(encoding='utf-8-sig')
        lines = text.splitlines()
        banners = [idx for idx, line in enumerate(lines) if line.startswith(SECTION_CSV_MARKER)]

        # metadata
        out["metadata"] = pd.read_csv(
            filepath_or_buffer=StringIO("\n".join(line for line in lines[0:banners[0]] if line.strip())),
            sep=";", header=None, dtype=str, keep_default_na=False, names=list(range(12)),
        )

        # data blocks
        for idx, start_idx in enumerate(banners):
            end_idx = banners[idx + 1] if idx + 1 < len(banners) else len(lines)
            banner = lines[start_idx].split(";")

            # name in medtronic csv has either specific name on 4th element
            # if it is just dashes fall back to device name (2nd element)
            name = banner[4].strip(" -") or banner[2]

            block = lines[start_idx + 1:end_idx]
            if not block or not block[0].startswith(HEADER_START):
                continue

            out[name] = pd.read_csv(
                filepath_or_buffer=StringIO("\n".join(line for line in block if line.strip())),
                sep=";", dtype=str, keep_default_na=False,
            )

        return out


if __name__ == "__main__":
    ingestor = Ingestor(filepath=r"C:\Users\ninja\Documents\code\diabetes-analysis\data\test.csv")
    print(f"Successfully loaded and parsed data!")
    print(f"CGM Readings extracted: {len(ingestor.cgm_data)}")
    print(f"Event Triggers extracted: {len(ingestor.event_data)}")

    print("\n--- Event Triggers Preview ---")
    print(ingestor.event_data.head())
    print("\n--- CGM Readings Preview ---")
    print(ingestor.cgm_data.head())