from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


def baseline_score(current: float, baseline: float) -> float:
    """Map a positive observation/baseline ratio to a bounded 0..100 score.

    A value equal to baseline maps to 50. A doubling moves materially above 50,
    and a halving moves materially below 50. The tanh transform keeps outliers
    from dominating the composite.
    """
    current = max(float(current), 1e-6)
    baseline = max(float(baseline), 1e-6)
    log_ratio = math.log(current / baseline, 2)
    return round(max(0.0, min(100.0, 50.0 + 42.0 * math.tanh(log_ratio))), 2)


def weighted_index(scores: Mapping[str, float], weights: Mapping[str, float]) -> float:
    usable = [(scores[k], weights[k]) for k in weights if k in scores and weights[k] > 0]
    if not usable:
        return 50.0
    numerator = sum(score * weight for score, weight in usable)
    denominator = sum(weight for _, weight in usable)
    return round(numerator / denominator, 2)


@dataclass(frozen=True)
class ActivityBaselines:
    person: float = 35.0
    car: float = 45.0
    motorcycle: float = 12.0
    bus: float = 8.0
    truck: float = 14.0
    boat: float = 3.0

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


def build_activity_index(counts: Mapping[str, int], baselines: ActivityBaselines | None = None) -> tuple[float, dict[str, float]]:
    baseline_map = (baselines or ActivityBaselines()).as_dict()
    scores = {name: baseline_score(counts.get(name, 0) + 1, value + 1) for name, value in baseline_map.items()}
    weights = {"person": 0.15, "car": 0.18, "motorcycle": 0.07, "bus": 0.14, "truck": 0.31, "boat": 0.15}
    return weighted_index(scores, weights), scores
