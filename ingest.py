from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from io import StringIO

SECTION_CSV_MARKER = "-------"

#control string to check if header starts correctly
HEADER_START = "Index;Date;Time"

#TODO metadata parser

def parse_section(df: pd.DataFrame) -> pd.DataFrame:
    df = df.replace("", pd.NA)

    #combines date and time columns into a single "Timestamp"
    if "Date" in df.columns and "Time" in df.columns:
        df["Timestamp"] = pd.to_datetime(
            df["Date"] + " " + df["Time"],
            format="%Y-%m-%d %H:%M:%S"
        )
    #converts ',' in numbers to '.' (ex: 3,14 => 3.14)
    for col in df.columns:
        if col in {"Index", "Date", "Time", "Timestamp"}:
            continue
        conv = pd.to_numeric(
            df[col].astype(str).str.replace(",", ".", regex=False),
        )
        # apply conversion only if all non-null entries convert cleanly
        if conv.notna().sum() > 0 and conv.notna().sum() == df[col].notna().sum():
            df[col] = conv

    return df.dropna(axis=1, how="all")


class Ingestor:
    def __init__(self, filepath, target_interval = 5):
        self.filepath = Path(filepath)
        self.target_interval = target_interval
        self.raw_data = self._load_raw_data()


    def _load_raw_data(self) -> dict[str,pd.DataFrame]:
        out = {}

        text = self.filepath.read_text(encoding='utf-8-sig')
        lines = text.splitlines()
        banners = [idx for idx, line in enumerate(lines) if line.startswith(SECTION_CSV_MARKER)]

        #metadata, doesnt parse correctly
        out["metadata"] = pd.read_csv(
            filepath_or_buffer = StringIO("\n".join(line for line in lines[0:banners[0]] if line.strip())),
            sep=";", header=None, dtype=str, keep_default_na=False, names=range(12),
        )

        #data blocks
        for idx, start_idx in enumerate(banners):
            end_idx = banners[idx + 1] if idx + 1 < len(banners) else len(lines)
            banner = lines[start_idx].split(";")
            #name in medtronic csv has either specific name on 4th element
            #if it is just dashes fall back to device name (2nd element)
            name = banner[4].strip(" -") or banner[2]

            block = lines[start_idx + 1:end_idx]
            if not block or not block[0].startswith(HEADER_START):
                continue
            out[name] = pd.read_csv(
                filepath_or_buffer=StringIO("\n".join(line for line in block if line.strip())),
                sep=";", header=None, dtype=str, keep_default_na=False,
            )
        return out


if __name__ == "__main__":
    Ingestor(filepath = r"C:\Users\ninja\Documents\code\diabetes-analysis\data\test.csv")

