import unittest

from src.game_state import GameState
from src.main import _handle_click


class ClickSoundTests(unittest.TestCase):
    class RendererStub:
        @staticmethod
        def cell_at(position: tuple[int, int]) -> int:
            return position[0]

    class SoundStub:
        def __init__(self) -> None:
            self.players: list[str] = []
            self.winners: list[str] = []
            self.draws = 0

        def play_player(self, player: str) -> None:
            self.players.append(player)

        def play_winner(self, winner: str) -> None:
            self.winners.append(winner)

        def play_draw(self) -> None:
            self.draws += 1

    def test_placing_cow_plays_cow_sound(self) -> None:
        state = GameState()
        sounds = self.SoundStub()

        _handle_click("cow", (5, 0), state, self.RendererStub(), sounds)

        self.assertEqual(state.board[5], "cow")
        self.assertEqual(sounds.players, ["cow"])

    def test_cow_can_select_and_move_after_all_cows_are_placed(self) -> None:
        state = GameState()
        state.board = [None] * 16
        for index in (0, 3, 12, 15):
            state.board[index] = "tiger"
        state.board[5] = "cow"
        state.cows_placed = 12
        state.current_turn = "cow"
        sounds = self.SoundStub()

        _handle_click("cow", (5, 0), state, self.RendererStub(), sounds)
        _handle_click("cow", (6, 0), state, self.RendererStub(), sounds)

        self.assertIsNone(state.board[5])
        self.assertEqual(state.board[6], "cow")
        self.assertEqual(state.current_turn, "tiger")
        self.assertEqual(sounds.players, ["cow", "cow"])

    def test_selecting_tiger_plays_tiger_sound(self) -> None:
        state = GameState(current_turn="tiger")
        sounds = self.SoundStub()

        _handle_click("tiger", (0, 0), state, self.RendererStub(), sounds)

        self.assertEqual(state.selected_tiger, 0)
        self.assertEqual(sounds.players, ["tiger"])

    def test_failed_click_does_not_play_a_player_sound(self) -> None:
        state = GameState()
        sounds = self.SoundStub()

        _handle_click("cow", (0, 0), state, self.RendererStub(), sounds)

        self.assertEqual(sounds.players, [])

    def test_cow_win_plays_only_cow_victory_sound(self) -> None:
        state = GameState()
        state.board = ["cow"] * 16
        for index in (0, 3, 12, 15):
            state.board[index] = "tiger"
        state.board[5] = None
        state.board[6] = None
        state.cows_placed = 10
        state.current_turn = "cow"
        sounds = self.SoundStub()

        _handle_click("cow", (5, 0), state, self.RendererStub(), sounds)

        self.assertEqual(state.winner, "cow")
        self.assertEqual(sounds.players, [])
        self.assertEqual(sounds.winners, ["cow"])

    def test_tiger_winning_capture_plays_only_tiger_victory_sound(self) -> None:
        state = GameState()
        state.board = [None] * 16
        state.board[5] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = 12
        state.cows_captured = 11
        state.current_turn = "tiger"
        sounds = self.SoundStub()

        _handle_click("tiger", (5, 0), state, self.RendererStub(), sounds)
        _handle_click("tiger", (7, 0), state, self.RendererStub(), sounds)

        self.assertEqual(state.winner, "tiger")
        self.assertEqual(sounds.players, ["tiger"])
        self.assertEqual(sounds.winners, ["tiger"])


if __name__ == "__main__":
    unittest.main()
