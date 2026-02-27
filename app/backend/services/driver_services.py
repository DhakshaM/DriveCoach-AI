from pathlib import Path
from backend.registry.trip_registry import TripRegistry
from backend.processing.severity import assign_severity

DATA_ROOT = Path("data/trips")
_registry = TripRegistry(DATA_ROOT)


def list_trips(driver_id: str):
    """
    Return list of trip IDs for a driver
    """
    driver_dir = DATA_ROOT / driver_id
    print("Looking for trips in:", driver_dir.resolve())
    print("Exists:", driver_dir.exists())
    if driver_dir.exists():
        print("Contents:", list(driver_dir.iterdir()))
    if not driver_dir.exists():
        return []

    return [
        d.name
        for d in driver_dir.iterdir()
        if d.is_dir()
    ]


def analyze_trip(driver_id: str, trip_id: str):
    """
    Run full pipeline for ONE trip
    """
    print(f">>> DRIVER SERVICE: analyzing {driver_id}/{trip_id}")

    results = _registry.process_trip(driver_id, trip_id)

    if not results:
        return {
            "status": "empty",
            "message": "No valid trip data"
        }

    r = results[0]  # we already enforce single segment

    return {
        "status": "ok",
        "trip_id": trip_id,
        "window_index": r["window_index"],
        "severity": r["severity"],
        "summary": r["summary"],
        "coaching": r["coaching"]
    }

def load_segment_severities_for_stream(driver_id: str, trip_id: str, max_segments=15):
    df = _registry._load_trip_df(driver_id, trip_id)

    severities = []
    for idx, row in df.iloc[:max_segments].iterrows():
        sev = assign_severity(row.to_dict())
        severities.append({
            "segment_index": idx,
            "severity": sev
        })

    return severities

def analyze_trip_segment(driver_id: str, trip_id: str, segment_idx: int):
    return _registry.process_trip_segment(driver_id, trip_id, segment_idx)

def get_segment_count(driver_id: str, trip_id: str) -> int:
    return _registry.list_segments(driver_id, trip_id)

def get_segments(driver_id, trip_id):
    return _registry.list_segments(driver_id, trip_id)

def analyze_segment(driver_id, trip_id, segment_idx):
    return _registry.process_trip_segment(driver_id, trip_id, segment_idx)

def get_segment_severities(driver_id: str, trip_id: str):
    return _registry.list_segment_severities(driver_id, trip_id)
