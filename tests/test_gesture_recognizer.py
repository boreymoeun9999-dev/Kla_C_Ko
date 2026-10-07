import unittest

from src.gesture_recognizer import (
    BoardThemeGestureRecognizer,
    GestureRecognizer,
    detect_board_theme_gesture,
)


def _hand_landmarks(extended_fingers: set[str]) -> list[tuple[float, float]]:
    landmarks = [(0.5, 0.9)] * 21
    finger_parts = (
        ("index", 5, 6, 7, 8, 0.37),
        ("middle", 9, 10, 11, 12, 0.45),
        ("ring", 13, 14, 15, 16, 0.55),
        ("pinky", 17, 18, 19, 20, 0.63),
    )
    for finger, mcp, pip, dip, tip, x in finger_parts:
        landmarks[mcp] = (x, 0.68)
        landmarks[pip] = (x, 0.52)
        landmarks[dip] = (x, 0.37 if finger in extended_fingers else 0.66)
        landmarks[tip] = (x, 0.18 if finger in extended_fingers else 0.74)
    return landmarks


class GestureRecognizerTests(unittest.TestCase):
    def test_pinch_grabs_and_release_commits_at_release_position(self) -> None:
        recognizer = GestureRecognizer()
        self.assertEqual(recognizer.update((0.1, 0.1, False)), ((0.1, 0.1), False))
        self.assertEqual(recognizer.update((0.1, 0.1, True)), ((0.1, 0.1), False))
        self.assertEqual(recognizer.update((0.8, 0.8, True)), ((0.8, 0.8), False))
        self.assertEqual(recognizer.update((0.8, 0.8, False)), ((0.8, 0.8), True))

    def test_releasing_after_no_pinch_does_not_trigger_a_move(self) -> None:
        recognizer = GestureRecognizer()
        self.assertFalse(recognizer.update((0.5, 0.5, False))[1])

    def test_losing_hand_during_pinch_cancels_without_triggering_a_move(self) -> None:
        recognizer = GestureRecognizer()
        recognizer.update((0.2, 0.2, True))
        self.assertEqual(recognizer.update(None), (None, False))
        self.assertEqual(recognizer.update((0.8, 0.8, False)), ((0.8, 0.8), False))

    def test_board_theme_gesture_recognizes_four_requested_poses(self) -> None:
        cases = (
            ({"index"}, "index"),
            ({"middle"}, "middle"),
            ({"index", "middle"}, "two"),
            ({"pinky"}, "pinky"),
        )
        for extended_fingers, expected in cases:
            with self.subTest(gesture=expected):
                self.assertEqual(
                    detect_board_theme_gesture(_hand_landmarks(extended_fingers)),
                    expected,
                )

    def test_other_hand_shapes_and_pinching_do_not_select_a_theme(self) -> None:
        self.assertIsNone(detect_board_theme_gesture(_hand_landmarks(set())))
        self.assertIsNone(
            detect_board_theme_gesture(_hand_landmarks({"index", "pinky"}))
        )
        self.assertIsNone(
            detect_board_theme_gesture(_hand_landmarks({"index"}), is_pinching=True)
        )

    def test_theme_gesture_requires_hold_and_triggers_once_per_pose(self) -> None:
        recognizer = BoardThemeGestureRecognizer(required_frames=3)

        self.assertIsNone(recognizer.update("middle"))
        self.assertIsNone(recognizer.update("middle"))
        self.assertEqual(recognizer.update("middle"), 1)
        self.assertIsNone(recognizer.update("middle"))
        self.assertIsNone(recognizer.update(None))
        self.assertIsNone(recognizer.update("pinky"))
        self.assertIsNone(recognizer.update("pinky"))
        self.assertEqual(recognizer.update("pinky"), 3)


if __name__ == "__main__":
    unittest.main()
