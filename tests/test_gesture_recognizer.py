import unittest

from src.gesture_recognizer import GestureRecognizer


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


if __name__ == "__main__":
    unittest.main()
