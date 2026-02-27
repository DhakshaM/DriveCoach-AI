# backend/processing/merger.py

import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from datetime import timedelta

# ================= CONFIG =================

WINDOW_SECONDS = 30
IMU_HZ = 25
DT = 1 / IMU_HZ

HARSH_BRAKE_G = -0.4
HARSH_ACCEL_G = 0.4
LATERAL_G_THRESH = 0.35
YAW_RATE_THRESH = 0.3
BUMP_G_THRESH = 0.3

DEBUG = False  # turn ON when debugging

# ==========================================


def _log(msg):
    if DEBUG:
        print(f"[MERGER] {msg}")


def _load_csv(path, index_col="timestamp"):
    if not path.exists():
        raise FileNotFoundError(f"Missing sensor file: {path}")

    df = pd.read_csv(path, parse_dates=[index_col])
    df.set_index(index_col, inplace=True)
    df.sort_index(inplace=True)

    _log(f"Loaded {path.name} ({len(df)} rows)")
    return df


def merge_sensor_csvs(location_csv, accel_csv, gyro_csv, max_segments=None):
    """
    Merge GPS + IMU sensor CSVs into windowed feature dataframe.

    Returns:
        pd.DataFrame where each row corresponds to a WINDOW_SECONDS segment.
    """

    # ---------- Load ----------
    location_df = _load_csv(location_csv)
    accel_df = _load_csv(accel_csv)
    gyro_df = _load_csv(gyro_csv)

    # ---------- Validation ----------
    if location_df.empty or accel_df.empty or gyro_df.empty:
        raise ValueError("One or more sensor CSVs are empty")

    timestamps = location_df.index
    features = []

    # ---------- Windowed feature extraction ----------
    for start_time in timestamps:
        end_time = start_time + timedelta(seconds=WINDOW_SECONDS)
        if end_time > timestamps[-1]:
            break

        accel_win = accel_df[start_time:end_time]
        gyro_win = gyro_df[start_time:end_time]
        loc_win = location_df[start_time:end_time]

        # Require sufficient IMU coverage
        min_samples = 0.7 * WINDOW_SECONDS * IMU_HZ
        if len(accel_win) < min_samples:
            _log(f"Skipping window @ {start_time} (insufficient IMU)")
            continue

        feat = {}

        # ---------- Speed ----------
        speeds = loc_win["speed"].dropna()
        feat["avg_speed_kmh"] = round(speeds.mean() * 3.6, 1) if len(speeds) else 0.0
        feat["max_speed_kmh"] = round(speeds.max() * 3.6, 1) if len(speeds) else 0.0
        feat["speed_variance"] = round(speeds.var(), 2) if len(speeds) > 1 else 0.0

        # ---------- Longitudinal events ----------
        ay = accel_win["accelerationY"]
        feat["harsh_brake_count"] = int((ay < HARSH_BRAKE_G).sum())
        feat["harsh_accel_count"] = int((ay > HARSH_ACCEL_G).sum())

        # ---------- Cornering ----------
        lateral = accel_win["accelerationX"].abs() > LATERAL_G_THRESH
        yaw = gyro_win["rotationRateZ"].abs() > YAW_RATE_THRESH
        feat["sharp_corner_count"] = int((lateral & yaw).sum())

        # ---------- Bumps ----------
        z_adj = accel_win["accelerationZ"] + 1.0  # remove gravity
        peaks, _ = find_peaks(z_adj.abs(), height=BUMP_G_THRESH)
        feat["bump_count"] = int(len(peaks))

        # ---------- Jerk ----------
        jerk = np.diff(ay) / DT
        feat["mean_abs_jerk"] = round(float(np.mean(np.abs(jerk))), 3) if len(jerk) else 0.0

        # ---------- Yaw stability ----------
        feat["yaw_variance"] = round(float(gyro_win["rotationRateZ"].var()), 6)

        features.append(feat)
        if max_segments is not None and len(features) >= max_segments:
            _log(f"Reached max_segments={max_segments}, stopping early")
            break

    df = pd.DataFrame(features)
    _log(f"Generated {len(df)} windows")

    return df
