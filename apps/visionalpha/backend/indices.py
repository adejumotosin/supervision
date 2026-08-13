from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping


SMOOTHING = 0.25


def baseline_score(current: float, baseline: float) -> float:
    """Map a positive observation/baseline ratio to a bounded 0..100 score.

    A value equal to baseline maps to 50. The log-ratio plus tanh transform
    keeps large temporary spikes from dominating a domain composite.
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


def normalize_per_minute(values: Mapping[str, float], duration_seconds: float) -> dict[str, float]:
    """Normalize track counts to rates so clips of different lengths are comparable."""
    if duration_seconds <= 0:
        return {name: 0.0 for name in values}
    minutes = duration_seconds / 60.0
    return {name: round(float(value) / minutes, 4) for name, value in values.items()}


def _feature_scores(values: Mapping[str, float], baselines: Mapping[str, float]) -> dict[str, float]:
    return {
        name: baseline_score(values.get(name, 0.0) + SMOOTHING, baseline + SMOOTHING)
        for name, baseline in baselines.items()
    }


@dataclass(frozen=True)
class ActivityBaselines:
    """Provisional unique-track rates per minute for the broad activity composite."""

    person: float = 35.0
    car: float = 45.0
    motorcycle: float = 12.0
    bus: float = 8.0
    truck: float = 14.0
    boat: float = 3.0

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PortLogisticsBaselines:
    """Provisional per-minute rates for the first vertical, Port & Logistics."""

    car: float = 18.0
    bus: float = 2.0
    truck: float = 8.0
    boat: float = 0.8

    def as_dict(self) -> dict[str, float]:
        return self.__dict__.copy()


def build_activity_index(
    rates_per_minute: Mapping[str, float],
    baselines: ActivityBaselines | None = None,
) -> tuple[float, dict[str, float]]:
    baseline_map = (baselines or ActivityBaselines()).as_dict()
    scores = _feature_scores(rates_per_minute, baseline_map)
    weights = {
        "person": 0.15,
        "car": 0.18,
        "motorcycle": 0.07,
        "bus": 0.14,
        "truck": 0.31,
        "boat": 0.15,
    }
    return weighted_index(scores, weights), scores


def build_port_logistics_index(
    rates_per_minute: Mapping[str, float],
    baselines: PortLogisticsBaselines | None = None,
) -> tuple[float, dict[str, float]]:
    baseline_map = (baselines or PortLogisticsBaselines()).as_dict()
    scores = _feature_scores(rates_per_minute, baseline_map)
    weights = {
        "truck": 0.50,
        "boat": 0.25,
        "car": 0.15,
        "bus": 0.10,
    }
    return weighted_index(scores, weights), scores
