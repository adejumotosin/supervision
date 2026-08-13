from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import cv2
import supervision as sv
from ultralytics import YOLO

from .indices import build_activity_index, build_port_logistics_index, normalize_per_minute

COCO_CLASSES = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    8: "boat",
}

ENGINE_VERSION = "yolo-supervision-phase3-v1"
_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(os.getenv("VISION_MODEL", "yolo11n.pt"))
    return _model


def analyze_video(path: str | Path, sample_every: int = 3, confidence: float = 0.35) -> dict:
    sample_every = max(1, int(sample_every))
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Unable to open video")

    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    effective_fps = max(0.1, fps / sample_every)
    tracker = sv.ByteTrack(frame_rate=max(1, int(round(effective_fps))))
    model = get_model()
    seen_tracks: dict[str, set[int]] = defaultdict(set)
    raw_detections: dict[str, int] = defaultdict(int)
    frames_total = 0
    frames_processed = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frames_total += 1
            if frames_total % sample_every != 0:
                continue

            frames_processed += 1
            result = model(frame, verbose=False, conf=confidence)[0]
            detections = sv.Detections.from_ultralytics(result)
            if len(detections) == 0:
                continue

            keep = [i for i, class_id in enumerate(detections.class_id) if int(class_id) in COCO_CLASSES]
            detections = detections[keep]
            if len(detections) == 0:
                continue

            tracked = tracker.update_with_detections(detections)
            for class_id, tracker_id in zip(tracked.class_id, tracked.tracker_id):
                name = COCO_CLASSES[int(class_id)]
                raw_detections[name] += 1
                if tracker_id is not None:
                    seen_tracks[name].add(int(tracker_id))
    finally:
        capture.release()

    unique_counts = {name: len(ids) for name, ids in seen_tracks.items()}
    for name in COCO_CLASSES.values():
        unique_counts.setdefault(name, 0)
        raw_detections.setdefault(name, 0)

    duration_seconds = round(frames_total / max(fps, 1e-6), 3)
    rates_per_minute = normalize_per_minute(unique_counts, duration_seconds)

    activity_index, feature_scores = build_activity_index(rates_per_minute)
    port_logistics_index, port_feature_scores = build_port_logistics_index(rates_per_minute)

    return {
        "engine": "yolo_supervision",
        "engine_version": ENGINE_VERSION,
        "frames_total": frames_total,
        "frames_processed": frames_processed,
        "video_fps": round(fps, 3),
        "effective_fps": round(effective_fps, 3),
        "sample_every": sample_every,
        "duration_seconds": duration_seconds,
        "unique_tracks": sum(unique_counts.values()),
        "counts": unique_counts,
        "rates_per_minute": rates_per_minute,
        "raw_detections": dict(raw_detections),
        "activity_index": activity_index,
        "feature_scores": feature_scores,
        "domain_indices": {
            "economic_activity": activity_index,
            "port_logistics": port_logistics_index,
        },
        "domain_feature_scores": {
            "port_logistics": port_feature_scores,
        },
        "methodology": (
            "Unique tracked objects are normalized to per-minute rates before comparison with "
            "baseline rates. Domain baselines are provisional until calibrated by location, camera, "
            "hour, weekday and season."
        ),
    }
