# backend/processing/severity.py

"""
IMPORTANT:
This file MUST emit the exact textual format used during LLM training.
Do NOT change wording, bullet style, or units unless you re-train the model.
"""

DEBUG = False


def _log(msg):
    if DEBUG:
        print(f"[SEVERITY] {msg}")


def build_llm_summary(feature_row: dict) -> str:
    """
    Builds the EXACT summary string format used for LLM coaching.
    This is the ONLY string passed to the LLM.
    """

    avg_speed = round(feature_row.get("avg_speed_kmh", 0.0), 1)
    max_speed = round(feature_row.get("max_speed_kmh", 0.0), 1)
    speed_var = round(feature_row.get("speed_variance", 0.0), 1)

    harsh_brakes = int(feature_row.get("harsh_brake_count", 0))
    harsh_accels = int(feature_row.get("harsh_accel_count", 0))
    sharp_corners = int(feature_row.get("sharp_corner_count", 0))
    bumps = int(feature_row.get("bump_count", 0))
    mean_jerk = round(feature_row.get("mean_abs_jerk", 0.0), 2)
    yaw_var = round(feature_row.get("yaw_variance", 0.0), 3)

    summary = f"""Driving sensor summary (30s segment):
• Avg/Max speed: {avg_speed}/{max_speed} km/h (variance {speed_var})
• Harsh brakes: {harsh_brakes}
• Harsh accelerations: {harsh_accels}
• Sharp corners: {sharp_corners}
• Bumps: {bumps}
• Mean jerk: {mean_jerk} m/s³
• Yaw variance: {yaw_var}"""

    _log(summary)
    return summary


def assign_severity(feature_row: dict) -> str:
    """
    Optional helper for UI coloring / aggregation.
    NOT used for LLM prompting.
    """

    score = 0

    if feature_row.get("harsh_brake_count", 0) > 3:
        score += 2
    if feature_row.get("harsh_accel_count", 0) > 3:
        score += 2
    if feature_row.get("sharp_corner_count", 0) > 3:
        score += 2
    if feature_row.get("bump_count", 0) > 3:
        score += 1
    if feature_row.get("mean_abs_jerk", 0) > 2.5:
        score += 2
    if feature_row.get("avg_speed_kmh", 0) > 60:
        score += 2

    if score >= 7:
        return "HIGH"
    elif score >= 4:
        return "MEDIUM"
    else:
        return "LOW"
