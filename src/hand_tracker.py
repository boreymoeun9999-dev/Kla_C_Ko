from __future__ import annotations

import time
from typing import NamedTuple

import cv2
import mediapipe as mp
from cv2.typing import MatLike
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from src.config import HAND_MODEL_PATH
from src.gesture_recognizer import detect_board_theme_gesture


HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)


class HandObservation(NamedTuple):
    x: float
    y: float
    is_pinching: bool
    handedness: str
    theme_gesture: str | None = None


class HandTracker:
    def __init__(self) -> None:
        if not HAND_MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Hand tracking model not found: {HAND_MODEL_PATH}. "
                "See the setup instructions in README.md."
            )
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._timestamp_ms = 0

    def process(self, mirrored_frame: MatLike) -> HandObservation | None:
        rgb_frame = cv2.cvtColor(mirrored_frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = max(time.monotonic_ns() // 1_000_000, self._timestamp_ms + 1)
        self._timestamp_ms = timestamp_ms
        results = self._landmarker.detect_for_video(image, timestamp_ms)
        if not results.hand_landmarks or not results.handedness:
            return None

        landmarks = results.hand_landmarks[0]
        handedness = results.handedness[0][0].category_name
        height, width = mirrored_frame.shape[:2]
        for start, end in HAND_CONNECTIONS:
            start_point = (int(landmarks[start].x * width), int(landmarks[start].y * height))
            end_point = (int(landmarks[end].x * width), int(landmarks[end].y * height))
            cv2.line(mirrored_frame, start_point, end_point, (75, 211, 150), 2)
        for index in (4, 8):
            point = (int(landmarks[index].x * width), int(landmarks[index].y * height))
            cv2.circle(mirrored_frame, point, 7, (255, 210, 80), -1)

        index_tip = landmarks[8]
        thumb_tip = landmarks[4]
        pinch_distance = (
            (index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2
        ) ** 0.5
        is_pinching = pinch_distance < 0.045
        return HandObservation(
            index_tip.x,
            index_tip.y,
            is_pinching,
            handedness,
            detect_board_theme_gesture(
                [(landmark.x, landmark.y) for landmark in landmarks],
                is_pinching,
            ),
        )

    def close(self) -> None:
        self._landmarker.close()
