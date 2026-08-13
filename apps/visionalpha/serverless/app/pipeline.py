from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .indices import build_motion_index


class CentroidTracker:
    def __init__(self, max_distance: float = 90.0, max_missed: int = 4) -> None:
        self.max_distance = max_distance
        self.max_missed = max_missed
        self.next_id = 1
        self.tracks: dict[int, tuple[tuple[float, float], int]] = {}
        self.seen_ids: set[int] = set()

    def update(self, boxes: list[list[float]]) -> None:
        centroids = [
            ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)
            for box in boxes
        ]
        unmatched = set(range(len(centroids)))
        updated: dict[int, tuple[tuple[float, float], int]] = {}

        for track_id, (previous, missed) in self.tracks.items():
            best_index = None
            best_distance = self.max_distance
            for index in unmatched:
                current = centroids[index]
                distance = float(
                    np.hypot(
                        current[0] - previous[0],
                        current[1] - previous[1],
                    )
                )
                if distance < best_distance:
                    best_distance = distance
                    best_index = index
            if best_index is not None:
                updated[track_id] = (centroids[best_index], 0)
                unmatched.remove(best_index)
                self.seen_ids.add(track_id)
            elif missed + 1 <= self.max_missed:
                updated[track_id] = (previous, missed + 1)

        for index in unmatched:
            track_id = self.next_id
            self.next_id += 1
            updated[track_id] = (centroids[index], 0)
            self.seen_ids.add(track_id)

        self.tracks = updated


def analyze_video(path: str | Path, sample_every: int = 4) -> dict:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Unable to open video")

    subtractor = cv2.createBackgroundSubtractorMOG2(
        history=160,
        varThreshold=28,
        detectShadows=False,
    )
    tracker = CentroidTracker()
    frames_total = 0
    frames_processed = 0
    motion_ratios: list[float] = []

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frames_total += 1
            if frames_total % sample_every != 0:
                continue

            frames_processed += 1
            height, width = frame.shape[:2]
            mask = subtractor.apply(frame)
            mask = cv2.medianBlur(mask, 5)
            _, mask = cv2.threshold(mask, 180, 255, cv2.THRESH_BINARY)
            motion_ratios.append(
                float(np.count_nonzero(mask)) / float(mask.size)
            )

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )
            boxes: list[list[float]] = []
            min_area = max(180.0, float(width * height) * 0.0007)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                if w < 8 or h < 8:
                    continue
                boxes.append(
                    [float(x), float(y), float(x + w), float(y + h)]
                )
            tracker.update(boxes)
    finally:
        capture.release()

    avg_motion_ratio = (
        float(np.mean(motion_ratios)) if motion_ratios else 0.0
    )
    activity_index, feature_scores = build_motion_index(
        len(tracker.seen_ids), avg_motion_ratio
    )
    return {
        "frames_total": frames_total,
        "frames_processed": frames_processed,
        "unique_tracks": len(tracker.seen_ids),
        "counts": {"moving_objects": len(tracker.seen_ids)},
        "activity_index": activity_index,
        "feature_scores": feature_scores,
        "avg_motion_ratio": round(avg_motion_ratio, 5),
        "mode": "serverless_motion_proxy",
        "methodology": (
            "Motion contours with lightweight centroid association. "
            "The production YOLO + Supervision pipeline remains in the repository "
            "for container or GPU deployment."
        ),
    }
