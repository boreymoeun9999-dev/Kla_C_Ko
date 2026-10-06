import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

import src.main as game
from src.camera import open_player_cameras
from src.config import BOARD_LEFT, BOARD_TOP, CELL_SIZE
from src.gesture_recognizer import GestureRecognizer
from src.hand_tracker import HandObservation
from src.renderer import Renderer


class DualCameraTests(unittest.TestCase):
    def test_can_type_both_player_names_from_keyboard_before_starting(self) -> None:
        names_seen_in_game = []
        original_draw = Renderer.draw

        def record_draw(renderer, state, cursor, frames, messages, indices):
            names_seen_in_game.append(dict(renderer.player_names))
            original_draw(renderer, state, cursor, frames, messages, indices)

        pygame.init()
        events = [
            [
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="A"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r, unicode="r"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="i"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, unicode="\t"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, unicode="M"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode="e"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i, unicode="i"),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"),
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, button=1, pos=(680, 566)
                ),
            ],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with (
            patch.object(
                game,
                "open_player_cameras",
                return_value=(
                    {"tiger": None, "cow": None},
                    {"tiger": None, "cow": None},
                ),
            ),
            patch.object(pygame.event, "get", side_effect=events),
            patch.object(Renderer, "draw", record_draw),
        ):
            game.main()

        self.assertEqual(
            names_seen_in_game[0],
            {"tiger": "Ari", "cow": "Mei"},
        )

    def test_back_to_start_resets_game_and_returns_to_start_screen(self) -> None:
        start_screens = []
        game_states = []
        original_draw_start_screen = Renderer.draw_start_screen
        original_draw = Renderer.draw

        def record_start_screen(renderer, cursor=None):
            start_screens.append(dict(renderer.player_names))
            original_draw_start_screen(renderer, cursor)

        def record_draw(renderer, state, cursor, frames, messages, indices):
            game_states.append((state.cows_placed, state.current_turn))
            original_draw(renderer, state, cursor, frames, messages, indices)

        pygame.init()
        events = [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(680, 566))],
            [
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=(BOARD_LEFT + CELL_SIZE + CELL_SIZE // 2,
                         BOARD_TOP + CELL_SIZE + CELL_SIZE // 2),
                )
            ],
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1255, 717))],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with (
            patch.object(
                game,
                "open_player_cameras",
                return_value=(
                    {"tiger": None, "cow": None},
                    {"tiger": None, "cow": None},
                ),
            ),
            patch.object(pygame.event, "get", side_effect=events),
            patch.object(Renderer, "draw_start_screen", record_start_screen),
            patch.object(Renderer, "draw", record_draw),
        ):
            game.main()

        self.assertEqual(len(start_screens), 2)
        self.assertIn((1, "tiger"), game_states)
        self.assertIn((0, "cow"), game_states)

    def test_camera_pinch_and_release_starts_game_over_start_button(self) -> None:
        class CameraStub:
            device_index = 0

            def __init__(self) -> None:
                self.read_count = 0

            def read(self):
                self.read_count += 1
                return np.zeros((16, 16, 3), dtype=np.uint8)

            def close(self) -> None:
                pass

        class HandTrackerStub:
            def __init__(self) -> None:
                self.observations = iter(
                    (
                        HandObservation(0.1, 0.1, False, "Right"),
                        HandObservation(0.1, 0.1, True, "Right"),
                        HandObservation(0.5, 0.744, False, "Right"),
                    )
                )

            def process(self, frame):
                if frame.shape != (16, 16, 3):
                    raise AssertionError("Start-screen camera frame should reach tracking.")
                return next(self.observations)

        camera = CameraStub()
        gestures = {player: GestureRecognizer() for player in game.PLAYERS}
        cameras = {"tiger": camera, "cow": None}
        trackers = {"tiger": HandTrackerStub(), "cow": None}
        start_button_rect = pygame.Rect(530, 528, 300, 76)

        results = [
            game._camera_clicked_start(
                cameras,
                trackers,
                gestures,
                start_button_rect,
            )
            for _ in range(3)
        ]

        self.assertEqual(results, [(False, (136, 76)), (False, (136, 76)), (True, (680, 565))])
        self.assertEqual(camera.read_count, 3)

    def test_cow_camera_places_and_tiger_camera_selects_then_moves(self) -> None:
        snapshots = []
        camera_instances = []
        original_draw = Renderer.draw

        class CameraStub:
            def __init__(self, device_index: int) -> None:
                self.device_index = device_index
                self.closed = False
                camera_instances.append(self)

            def read(self):
                return np.full((16, 16, 3), self.device_index, dtype=np.uint8)

            def close(self) -> None:
                self.closed = True

        class HandTrackerStub:
            next_player = 0

            def __init__(self) -> None:
                self.player = HandTrackerStub.next_player
                HandTrackerStub.next_player += 1
                self.calls = 0

            def process(self, frame):
                if frame.shape != (16, 16, 3):
                    raise AssertionError("Both camera frames should reach hand tracking.")
                self.calls += 1
                if self.player == 0:
                    tiger_gestures = (
                        (0.125, 0.125, False),
                        (0.125, 0.125, False),
                        (0.125, 0.125, True),
                        (0.125, 0.125, True),
                        (0.125, 0.125, False),
                        (0.375, 0.125, True),
                        (0.375, 0.125, True),
                        (0.375, 0.125, False),
                        (0.375, 0.125, False),
                        (0.375, 0.125, False),
                    )
                    x, y, pinching = tiger_gestures[
                        min(self.calls - 1, len(tiger_gestures) - 1)
                    ]
                    return HandObservation(x, y, pinching, "Right")

                cow_gestures = (
                    (0.375, 0.375, False),
                    (0.375, 0.375, True),
                    (0.375, 0.375, False),
                    (0.375, 0.375, False),
                    (0.375, 0.375, False),
                    (0.375, 0.375, True),
                    (0.375, 0.375, True),
                    (0.375, 0.375, True),
                    (0.5, 0.125, True),
                    (0.5, 0.125, True),
                    (0.5, 0.125, False),
                )
                x, y, pinching = cow_gestures[
                    min(self.calls - 1, len(cow_gestures) - 1)
                ]
                return HandObservation(x, y, pinching, "Left")

            def close(self) -> None:
                pass

        def record_draw(renderer, state, cursor, frames, messages, camera_indices):
            snapshots.append(
                (
                    state.board.copy(),
                    state.current_turn,
                    state.selected_tiger,
                    {player: int(frame[0, 0, 0]) for player, frame in frames.items()},
                    dict(camera_indices),
                )
            )
            original_draw(renderer, state, cursor, frames, messages, camera_indices)

        pygame.init()
        events = [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(680, 566))],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [pygame.event.Event(pygame.QUIT)],
        ]
        cameras = {"tiger": CameraStub(0), "cow": CameraStub(2)}
        camera_messages = {"tiger": None, "cow": None}
        with (
            patch.object(
                game,
                "open_player_cameras",
                return_value=(cameras, camera_messages),
            ),
            patch.object(game, "HandTracker", HandTrackerStub),
            patch.object(pygame.event, "get", side_effect=events),
            patch.object(Renderer, "draw", record_draw),
        ):
            game.main()

        self.assertEqual(snapshots[0][1], "cow")
        self.assertEqual(snapshots[2][0][5], "cow")
        self.assertEqual(snapshots[2][1], "tiger")
        self.assertEqual(snapshots[4][2], 0)
        self.assertEqual(snapshots[7][0][0], None)
        self.assertEqual(snapshots[7][0][1], "tiger")
        self.assertEqual(snapshots[10][0][2], "cow")
        self.assertEqual(snapshots[0][3], {"tiger": 0, "cow": 2})
        self.assertEqual(snapshots[0][4], {"tiger": 0, "cow": 2})
        self.assertTrue(all(camera.closed for camera in camera_instances))

    def test_each_player_ignores_the_other_players_hand(self) -> None:
        left_hand = HandObservation(0.25, 0.5, True, "Left")
        right_hand = HandObservation(0.75, 0.5, True, "Right")

        self.assertEqual(game._hand_input_for_player("tiger", right_hand), (0.75, 0.5, True))
        self.assertIsNone(game._hand_input_for_player("tiger", left_hand))
        self.assertEqual(game._hand_input_for_player("cow", left_hand), (0.25, 0.5, True))
        self.assertIsNone(game._hand_input_for_player("cow", right_hand))

    def test_finds_second_camera_when_device_indices_are_not_contiguous(self) -> None:
        opened_cameras = []

        class CaptureStub:
            def __init__(self, device_index, backend):
                self.device_index = device_index
                self.backend = backend
                self.opened = device_index in (0, 2)
                self.released = False

            def isOpened(self):
                return self.opened

            def set(self, property_id, value):
                self.last_property = property_id
                self.last_value = value
                return True

            def read(self):
                return self.opened, np.zeros((4, 4, 3), dtype=np.uint8)

            def release(self):
                self.released = True

        def capture_factory(device_index, backend):
            capture = CaptureStub(device_index, backend)
            opened_cameras.append(capture)
            return capture

        with patch("src.camera.cv2.VideoCapture", side_effect=capture_factory):
            cameras, messages = open_player_cameras(("tiger", "cow"), max_device_index=3)

        tiger_camera = cameras["tiger"]
        cow_camera = cameras["cow"]
        self.assertIsNotNone(tiger_camera)
        self.assertIsNotNone(cow_camera)
        if tiger_camera is None or cow_camera is None:
            self.fail("Expected both available webcams to be assigned to players.")
        self.assertEqual(tiger_camera.device_index, 0)
        self.assertEqual(cow_camera.device_index, 2)
        self.assertIsNone(messages["tiger"])
        self.assertIsNone(messages["cow"])
        for camera in cameras.values():
            if camera is not None:
                camera.close()

    def test_only_one_available_camera_is_shared(self) -> None:
        class CaptureStub:
            def __init__(self, device_index, backend):
                self.device_index = device_index
                self.backend = backend
                self.opened = device_index == 0

            def isOpened(self):
                return self.opened

            def set(self, property_id, value):
                self.last_property = property_id
                self.last_value = value
                return True

            def read(self):
                return self.opened, np.zeros((4, 4, 3), dtype=np.uint8)

            def release(self):
                pass

        with patch(
            "src.camera.cv2.VideoCapture",
            side_effect=lambda device_index, backend: CaptureStub(device_index, backend),
        ):
            cameras, messages = open_player_cameras(("tiger", "cow"), max_device_index=1)

        self.assertIsNotNone(cameras["tiger"])
        self.assertIs(cameras["tiger"], cameras["cow"])
        self.assertIsNone(messages["tiger"])
        self.assertIsNone(messages["cow"])
        if cameras["tiger"] is not None:
            cameras["tiger"].close()

    def test_one_webcam_is_read_once_and_shown_to_both_players(self) -> None:
        snapshots = []
        original_draw = Renderer.draw

        class CameraStub:
            device_index = 0

            def __init__(self):
                self.read_count = 0
                self.close_count = 0

            def read(self):
                self.read_count += 1
                return np.full((16, 16, 3), 77, dtype=np.uint8)

            def close(self):
                self.close_count += 1

        class HandTrackerStub:
            instances = []

            def __init__(self):
                self.calls = 0
                self.instances.append(self)

            def process(self, _frame):
                if _frame.shape != (16, 16, 3):
                    raise AssertionError("Shared camera frame should reach hand tracking.")
                self.calls += 1
                return None

            def close(self):
                pass

        def record_draw(renderer, state, cursor, frames, messages, indices):
            snapshots.append(
                (frames["tiger"] is frames["cow"], dict(indices))
            )
            original_draw(renderer, state, cursor, frames, messages, indices)

        camera = CameraStub()
        pygame.init()
        events = [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(680, 566))],
            [],
            [],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with (
            patch.object(
                game,
                "open_player_cameras",
                return_value=(
                    {"tiger": camera, "cow": camera},
                    {"tiger": None, "cow": None},
                ),
            ),
            patch.object(game, "HandTracker", HandTrackerStub),
            patch.object(pygame.event, "get", side_effect=events),
            patch.object(Renderer, "draw", record_draw),
        ):
            game.main()

        self.assertEqual(len(HandTrackerStub.instances), 1)
        self.assertEqual(HandTrackerStub.instances[0].calls, 3)
        self.assertEqual(camera.read_count, 3)
        self.assertEqual(camera.close_count, 1)
        self.assertTrue(all(shared for shared, _ in snapshots))
        self.assertTrue(
            all(indices == {"tiger": 0, "cow": 0} for _, indices in snapshots)
        )

if __name__ == "__main__":
    unittest.main()
