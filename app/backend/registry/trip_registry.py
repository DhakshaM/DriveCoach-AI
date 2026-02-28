# backend/registry/trip_registry.py

from pathlib import Path
import pandas as pd

from backend.processing.merger import merge_sensor_csvs
from backend.processing.severity import build_llm_summary, assign_severity
from backend.llm.llm_engine import get_coaching_feedback
# from backend.llm.llm_engine import is_initialized

# if not is_initialized():
#     raise RuntimeError("LLM not initialized at app startup")
MAX_SEGMENTS = 15

class TripRegistry:
    """
    Central access point for trip-level operations.
    """

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    # --------------------------------------------------
    # Discovery
    # --------------------------------------------------

    def list_drivers(self):
        return sorted(
            p.name for p in self.data_root.iterdir()
            if p.is_dir()
        )

    def list_trips(self, driver_id: str):
        driver_dir = self.data_root / driver_id
        if not driver_dir.exists():
            return []

        return sorted(
            p.name for p in driver_dir.iterdir()
            if p.is_dir()
        )

    # --------------------------------------------------
    # Core pipeline
    # --------------------------------------------------

    def process_trip(self, driver_id: str, trip_id: str):
        """
        Legacy pipeline: analyze FIRST segment only.
        """
        segments = self.list_segments(driver_id, trip_id)

        if not segments:
            return []

        first_idx = segments[0]
        return [self.process_trip_segment(driver_id, trip_id, first_idx)]

            

    # --------------------------------------------------
    # Debug helpers
    # --------------------------------------------------

    def debug_trip(self, driver_id: str, trip_id: str, n=1):
        """
        Runs first n windows without calling the LLM.
        """

        from backend.llm import llm_engine
        old_stub = llm_engine.USE_STUB
        llm_engine.USE_STUB = True

        try:
            data = self.process_trip(driver_id, trip_id)
            return data[:n]
        finally:
            llm_engine.USE_STUB = old_stub

    def list_segments(self, driver_id: str, trip_id: str) -> int:
        """
        Return number of segments for a trip.
        """
        df = self._load_trip_df(driver_id, trip_id)

        # each row == one 30s window
        return list(df.index)

    def process_trip_segment(self, driver_id: str, trip_id: str, idx: int):
        df = self._load_trip_df(driver_id, trip_id)

        if idx not in df.index:
            raise ValueError("Invalid segment index")

        row_dict = df.loc[idx].to_dict()

        summary = build_llm_summary(row_dict)
        severity = assign_severity(row_dict)
        print(f">>> Calling Coach LLM for trip {trip_id}, window {idx}")
        coaching = get_coaching_feedback(summary, severity, True)
        
        print(f">>> ABOUT TO LOG TO DB: driver={driver_id}, trip={trip_id}, idx={idx}, coaching={repr(coaching[:60])}")

        return {
            "window_index": idx,
            "severity": severity,
            "summary": summary,
            "coaching": coaching,
        }
    
    def _load_trip_df(self, driver_id: str, trip_id: str):
        """
        Load and merge sensor CSVs into a dataframe.
        Each row corresponds to one 30s segment.
        """
        trip_dir = self.data_root / driver_id / trip_id

        if not trip_dir.exists():
            raise FileNotFoundError(f"Trip not found: {trip_dir}")

        loc = trip_dir / "location_data.csv"
        acc = trip_dir / "accelerometer_data.csv"
        gyro = trip_dir / "gyroscope_data.csv"

        for f in (loc, acc, gyro):
            if not f.exists():
                raise FileNotFoundError(f"Missing file: {f.name}")

        # 🔑 single source of truth for segmentation
        df = merge_sensor_csvs(loc, acc, gyro, max_segments=MAX_SEGMENTS)

        return df

    def list_segment_severities(self, driver_id: str, trip_id: str):
        """
        Returns severity per segment without calling the LLM.
        """
        df = self._load_trip_df(driver_id, trip_id)

        results = []
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            severity = assign_severity(row_dict)

            results.append({
                "segment_index": idx,
                "severity": severity
            })

        return results

