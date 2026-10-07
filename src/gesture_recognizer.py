from collections.abc import Sequence


HandInput = tuple[float, float, bool] | None
BOARD_THEME_GESTURES = {
    "index": 0,
    "middle": 1,
    "two": 2,
    "pinky": 3,
}
def detect_hand_gesture(
    landmarks: Sequence[tuple[float, float]],
    is_pinching: bool = False,
) -> str | None:
    if is_pinching or len(landmarks) < 21:
        return None

    wrist_x, wrist_y = landmarks[0]
    extended_fingers = []
    for finger, tip_index, pip_index in (
        ("index", 8, 6),
        ("middle", 12, 10),
        ("ring", 16, 14),
        ("pinky", 20, 18),
    ):
        tip_x, tip_y = landmarks[tip_index]
        pip_x, pip_y = landmarks[pip_index]
        tip_distance = (tip_x - wrist_x) ** 2 + (tip_y - wrist_y) ** 2
        pip_distance = (pip_x - wrist_x) ** 2 + (pip_y - wrist_y) ** 2
        if tip_distance > pip_distance * 1.18**2:
            extended_fingers.append(finger)

    if extended_fingers == ["index"]:
        return "index"
    if extended_fingers == ["middle"]:
        return "middle"
    if extended_fingers == ["index", "middle"]:
        return "two"
    if extended_fingers == ["pinky"]:
        return "pinky"
    return None


def detect_board_theme_gesture(
    landmarks: Sequence[tuple[float, float]],
    is_pinching: bool = False,
) -> str | None:
    gesture = detect_hand_gesture(landmarks, is_pinching)
    return gesture if gesture in BOARD_THEME_GESTURES else None


class BoardThemeGestureRecognizer:
    def __init__(self, required_frames: int = 8) -> None:
        if required_frames < 1:
            raise ValueError("required_frames must be at least 1")
        self._required_frames = required_frames
        self._candidate: str | None = None
        self._candidate_frames = 0
        self._active_gesture: str | None = None

    def update(self, gesture: str | None) -> int | None:
        if gesture not in BOARD_THEME_GESTURES:
            self._candidate = None
            self._candidate_frames = 0
            self._active_gesture = None
            return None

        if gesture == self._active_gesture:
            return None
        if gesture != self._candidate:
            self._candidate = gesture
            self._candidate_frames = 1
        else:
            self._candidate_frames += 1

        if self._candidate_frames < self._required_frames:
            return None

        self._active_gesture = gesture
        return BOARD_THEME_GESTURES[gesture]


class GestureRecognizer:
    """Treat a pinch as a grab and commit the move when the fingers release."""

    def __init__(self) -> None:
        self._pinching = False

    def update(self, hand: HandInput) -> tuple[tuple[float, float] | None, bool]:
        if hand is None:
            self._pinching = False
            return None, False

        x, y, is_pinching = hand
        clicked = self._pinching and not is_pinching
        self._pinching = is_pinching
        return (x, y), clicked


def map_to_board(
    position: Sequence[float],
    left: int,
    top: int,
    width: int,
    height: int,
) -> tuple[int, int]:
    x = max(0.0, min(1.0, position[0]))
    y = max(0.0, min(1.0, position[1]))
    return left + min(int(x * width), width - 1), top + min(int(y * height), height - 1)
