import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from src.ai_player import AI_DIFFICULTIES, play_ai_turn
import src.main as game
from src.game_state import GameState
from src.main import _configure_ai_opponent
from src.renderer import Renderer


class AIPlayerTests(unittest.TestCase):
    def test_cow_ai_places_a_cow_and_passes_turn_to_tiger(self) -> None:
        state = GameState()

        self.assertTrue(play_ai_turn(state))

        self.assertEqual(state.cows_placed, 1)
        self.assertEqual(state.board.count("cow"), 1)
        self.assertEqual(state.current_turn, "tiger")

    def test_tiger_ai_takes_a_winning_capture(self) -> None:
        state = GameState()
        state.board = [None] * 16
        state.board[5] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = 12
        state.cows_captured = 11
        state.current_turn = "tiger"

        self.assertTrue(play_ai_turn(state))

        self.assertEqual(state.cows_captured, 12)
        self.assertEqual(state.winner, "tiger")
        self.assertIsNone(state.current_turn)

    def test_cow_ai_moves_a_cow_after_all_are_placed(self) -> None:
        state = GameState()
        state.board = [None] * 16
        for index in (0, 3, 12, 15):
            state.board[index] = "tiger"
        state.board[5] = "cow"
        state.cows_placed = 12
        state.current_turn = "cow"

        self.assertTrue(play_ai_turn(state))

        self.assertEqual(state.board.count("cow"), 1)
        self.assertEqual(state.current_turn, "tiger")

    def test_ai_does_not_move_when_it_is_not_its_turn_or_game_is_over(self) -> None:
        state = GameState(current_turn=None)
        self.assertFalse(play_ai_turn(state))

        state.current_turn = "tiger"
        state.winner = "cow"
        self.assertFalse(play_ai_turn(state))

    def test_ai_strengths_map_to_search_depths(self) -> None:
        self.assertEqual(
            AI_DIFFICULTIES,
            {"Easy": 1, "Medium": 2, "Hard": 3, "Master": 5},
        )

    def test_ai_rejects_invalid_search_depth(self) -> None:
        state = GameState()
        self.assertFalse(play_ai_turn(state, depth=0))

    def test_selected_human_role_sets_the_opposite_ai_player(self) -> None:
        renderer = Renderer.__new__(Renderer)
        renderer.play_mode = "ai"
        renderer.human_player = "tiger"
        renderer.ai_player = None

        _configure_ai_opponent(renderer)

        self.assertEqual(renderer.ai_player, "cow")
        renderer.human_player = "cow"
        _configure_ai_opponent(renderer)
        self.assertEqual(renderer.ai_player, "tiger")
        renderer.play_mode = "two-player"
        _configure_ai_opponent(renderer)
        self.assertIsNone(renderer.ai_player)

    def test_start_screen_selection_starts_human_vs_computer_game(self) -> None:
        drawn_states = []
        pygame.init()
        start_events = [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=(800, 473)
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=(560, 515)
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=(820, 580)
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=(680, 630)
            ),
        ]
        events = [
            start_events,
            [],
            [pygame.event.Event(pygame.QUIT)],
        ]

        def record_draw(renderer, state, cursor, frames, messages, indices):
            drawn_states.append(
                (state.cows_placed, renderer.ai_player, renderer.ai_strength)
            )

        try:
            with (
                patch.object(
                    game,
                    "open_player_cameras",
                    return_value=(
                        {"tiger": None, "cow": None},
                        {"tiger": None, "cow": None},
                    ),
                ),
                patch.object(
                    game, "play_ai_turn", wraps=play_ai_turn
                ) as ai_turn,
                patch.object(pygame.event, "get", side_effect=events),
                patch.object(game.time, "monotonic", side_effect=(100.0, 200.0)),
                patch.object(Renderer, "draw", record_draw),
            ):
                game.main()
        finally:
            pygame.quit()

        self.assertIn((1, "cow", "Master"), drawn_states)
        ai_turn.assert_called_once()
        self.assertEqual(ai_turn.call_args.kwargs["depth"], 5)


if __name__ == "__main__":
    unittest.main()
