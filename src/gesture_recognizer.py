from collections.abc import Sequence


HandInput = tuple[float, float, bool] | None


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
