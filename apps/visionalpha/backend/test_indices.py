from .indices import (
    ActivityBaselines,
    PortLogisticsBaselines,
    baseline_score,
    build_activity_index,
    build_port_logistics_index,
    normalize_per_minute,
    weighted_index,
)


def test_baseline_maps_to_midpoint():
    assert baseline_score(10, 10) == 50.0


def test_scores_are_bounded():
    assert 0 <= baseline_score(0.001, 1000) <= 100
    assert 0 <= baseline_score(1000, 0.001) <= 100


def test_weighted_index():
    assert weighted_index({"a": 20, "b": 80}, {"a": 1, "b": 3}) == 65.0


def test_normalize_per_minute():
    assert normalize_per_minute({"truck": 10}, 120) == {"truck": 5.0}


def test_normalize_zero_duration_is_safe():
    assert normalize_per_minute({"truck": 10}, 0) == {"truck": 0.0}


def test_activity_index_shape():
    baselines = ActivityBaselines()
    score, features = build_activity_index(baselines.as_dict())
    assert 49 <= score <= 51
    assert "truck" in features


def test_port_logistics_baseline_maps_near_midpoint():
    baselines = PortLogisticsBaselines()
    score, features = build_port_logistics_index(baselines.as_dict())
    assert 49 <= score <= 51
    assert set(features) == {"car", "bus", "truck", "boat"}


def test_port_logistics_rises_with_truck_and_boat_activity():
    low, _ = build_port_logistics_index({"car": 18, "bus": 2, "truck": 4, "boat": 0.4})
    high, _ = build_port_logistics_index({"car": 18, "bus": 2, "truck": 16, "boat": 1.6})
    assert high > low
