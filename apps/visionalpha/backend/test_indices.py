from .indices import baseline_score, build_activity_index, weighted_index


def test_baseline_maps_to_midpoint():
    assert baseline_score(10, 10) == 50.0


def test_scores_are_bounded():
    assert 0 <= baseline_score(0.001, 1000) <= 100
    assert 0 <= baseline_score(1000, 0.001) <= 100


def test_weighted_index():
    assert weighted_index({"a": 20, "b": 80}, {"a": 1, "b": 3}) == 65.0


def test_activity_index_shape():
    score, features = build_activity_index({"person": 35, "car": 45, "motorcycle": 12, "bus": 8, "truck": 14, "boat": 3})
    assert 40 <= score <= 60
    assert "truck" in features
