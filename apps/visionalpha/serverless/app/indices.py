from __future__ import annotations

import math


def baseline_score(current: float, baseline: float) -> float:
    current = max(float(current), 1e-6)
    baseline = max(float(baseline), 1e-6)
    log_ratio = math.log(current / baseline, 2)
    return round(max(0.0, min(100.0, 50.0 + 42.0 * math.tanh(log_ratio))), 2)


def build_motion_index(
    unique_tracks: int, avg_motion_ratio: float
) -> tuple[float, dict[str, float]]:
    object_score = baseline_score(unique_tracks + 1, 18.0)
    motion_score = baseline_score(avg_motion_ratio + 0.001, 0.035)
    composite = round(object_score * 0.65 + motion_score * 0.35, 2)
    return composite, {
        "tracked_objects": object_score,
        "motion_intensity": motion_score,
    }
