import unittest

from src.game_rules import (
    BOARD_CELLS,
    STARTING_TIGER_CELLS,
    all_tigers_trapped,
    legal_cow_moves,
    legal_tiger_moves,
)
from src.game_state import TOTAL_COWS, TIGER_WIN_CAPTURES, GameState


class GameRulesTests(unittest.TestCase):
    def test_starts_with_four_corner_tigers_and_cow_turn(self) -> None:
        state = GameState()
        self.assertEqual(
            tuple(index for index, piece in enumerate(state.board) if piece == "tiger"),
            STARTING_TIGER_CELLS,
        )
        self.assertEqual(BOARD_CELLS, 16)
        self.assertEqual(TOTAL_COWS, 12)
        self.assertEqual(state.cows_placed, 0)
        self.assertEqual(state.current_turn, "cow")

    def test_cow_places_one_at_a_time_then_tiger_moves(self) -> None:
        state = GameState()
        self.assertFalse(state.place(-1))
        self.assertFalse(state.place(BOARD_CELLS))
        self.assertFalse(state.place(0))
        self.assertTrue(state.place(5))
        self.assertEqual(state.board[5], "cow")
        self.assertEqual(state.current_turn, "tiger")
        self.assertTrue(state.select_tiger(0))
        self.assertFalse(state.move_tiger(2))
        self.assertTrue(state.move_tiger(1))
        self.assertIsNone(state.board[0])
        self.assertEqual(state.board[1], "tiger")
        self.assertEqual(state.current_turn, "cow")
        self.assertEqual(state.cows_placed, 1)

    def test_tiger_move_must_be_adjacent_and_destination_empty(self) -> None:
        state = GameState()
        state.current_turn = "tiger"
        self.assertFalse(state.select_tiger(5))
        self.assertTrue(state.select_tiger(0))
        self.assertNotIn(2, legal_tiger_moves(state.board, 0))
        self.assertFalse(state.move_tiger(2))
        self.assertTrue(state.move_tiger(1))
        self.assertEqual(state.current_turn, "cow")

    def test_cow_moves_one_orthogonal_square_into_an_empty_cell(self) -> None:
        board: list[str | None] = [None] * BOARD_CELLS
        board[5] = "cow"
        board[1] = "tiger"
        self.assertEqual(legal_cow_moves(board, 5), (9, 4, 6))
        self.assertEqual(legal_cow_moves(board, -1), ())
        self.assertEqual(legal_cow_moves(board, 16), ())
        self.assertEqual(legal_cow_moves(board, 1), ())

    def test_cow_can_move_after_all_cows_are_placed(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[0] = "tiger"
        state.board[5] = "tiger"
        state.board[10] = "tiger"
        state.board[15] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = TOTAL_COWS
        state.current_turn = "cow"

        self.assertTrue(state.select_cow(6))
        self.assertFalse(state.move_cow(9))
        self.assertTrue(state.move_cow(7))
        self.assertIsNone(state.board[6])
        self.assertEqual(state.board[7], "cow")
        self.assertEqual(state.current_turn, "tiger")

    def test_cow_turn_follows_tiger_move_after_all_cows_are_placed(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[0] = "tiger"
        state.board[5] = "tiger"
        state.board[15] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = TOTAL_COWS
        state.current_turn = "tiger"

        self.assertTrue(state.select_tiger(5))
        self.assertTrue(state.move_tiger(9))
        self.assertEqual(state.current_turn, "cow")

    def test_tiger_can_jump_over_and_capture_cow_in_all_four_directions(self) -> None:
        cases = ((9, 5, 1), (5, 9, 13), (6, 5, 4), (5, 6, 7))
        for tiger_cell, cow_cell, landing_cell in cases:
            with self.subTest(direction=(tiger_cell, cow_cell, landing_cell)):
                state = GameState()
                state.board = [None] * BOARD_CELLS
                state.board[tiger_cell] = "tiger"
                state.board[cow_cell] = "cow"
                state.cows_placed = 1
                state.current_turn = "tiger"
                self.assertIn(landing_cell, legal_tiger_moves(state.board, tiger_cell))
                self.assertTrue(state.select_tiger(tiger_cell))
                self.assertTrue(state.move_tiger(landing_cell))
                self.assertEqual(state.board[landing_cell], "tiger")
                self.assertIsNone(state.board[cow_cell])
                self.assertEqual(state.cows_captured, 1)
                self.assertEqual(state.current_turn, "cow")

    def test_cow_can_place_again_after_tiger_captures_one(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[5] = "tiger"
        state.board[9] = "cow"
        state.cows_placed = 1
        state.current_turn = "tiger"
        self.assertTrue(state.select_tiger(5))
        self.assertTrue(state.move_tiger(13))
        self.assertTrue(state.place(9))
        self.assertEqual(state.board[9], "cow")
        self.assertEqual(state.cows_placed, 2)
        self.assertEqual(state.cows_captured, 1)

    def test_tiger_cannot_jump_cow_without_an_empty_landing_square(self) -> None:
        state = GameState()
        state.board = ["tiger", "cow", "cow", None] + [None] * (BOARD_CELLS - 4)
        state.current_turn = "tiger"
        self.assertNotIn(2, legal_tiger_moves(state.board, 0))
        self.assertTrue(state.select_tiger(0))
        self.assertFalse(state.move_tiger(2))
        self.assertEqual(state.board[1], "cow")
        self.assertEqual(state.cows_captured, 0)

    def test_cow_wins_when_every_tiger_is_trapped(self) -> None:
        state = GameState()
        state.board = ["cow"] * BOARD_CELLS
        for index in STARTING_TIGER_CELLS:
            state.board[index] = "tiger"
        state.board[5] = None
        state.board[6] = None
        state.cows_placed = TOTAL_COWS - 2
        state.current_turn = "cow"
        self.assertTrue(all_tigers_trapped(state.board))
        self.assertTrue(state.place(5))
        self.assertEqual(state.winner, "cow")
        self.assertTrue(state.is_over)

    def test_cow_wins_when_tigers_are_trapped_even_if_cows_cannot_move(self) -> None:
        state = GameState()
        state.board = ["cow"] * BOARD_CELLS
        for index in STARTING_TIGER_CELLS:
            state.board[index] = "tiger"
        state.board[5] = None
        state.cows_placed = TOTAL_COWS - 1
        state.current_turn = "cow"
        self.assertTrue(state.place(5))
        self.assertEqual(state.cows_placed, TOTAL_COWS)
        self.assertNotEqual(state.winner, "tiger")
        self.assertEqual(state.winner, "cow")
        self.assertIsNone(state.current_turn)
        self.assertTrue(state.is_over)

    def test_tiger_does_not_win_when_fewer_than_twelve_cows_are_captured(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[5] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = 12
        state.cows_captured = TIGER_WIN_CAPTURES - 2
        state.current_turn = "tiger"
        self.assertTrue(state.select_tiger(5))
        self.assertTrue(state.move_tiger(7))
        self.assertEqual(state.cows_captured, TIGER_WIN_CAPTURES - 1)
        self.assertIsNone(state.winner)
        self.assertEqual(state.current_turn, "tiger")

    def test_tiger_does_not_win_just_because_all_twelve_cows_are_placed(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[5] = "tiger"
        state.cows_placed = TOTAL_COWS - 1
        state.current_turn = "cow"
        self.assertTrue(state.place(0))
        self.assertEqual(state.cows_placed, TOTAL_COWS)
        self.assertIsNone(state.winner)
        self.assertEqual(state.current_turn, "tiger")
        self.assertFalse(state.is_over)
        self.assertTrue(state.select_tiger(5))
        self.assertFalse(state.place(1))

    def test_tiger_wins_only_after_eating_all_twelve_cows(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        state.board[5] = "tiger"
        state.board[6] = "cow"
        state.cows_placed = TOTAL_COWS
        state.cows_captured = TOTAL_COWS - 1
        state.current_turn = "tiger"
        self.assertTrue(state.select_tiger(5))
        self.assertTrue(state.move_tiger(7))
        self.assertEqual(state.cows_captured, TOTAL_COWS)
        self.assertEqual(state.winner, "tiger")
        self.assertTrue(state.is_over)

    def test_tiger_wins_when_last_cow_has_no_legal_move(self) -> None:
        state = GameState()
        state.board = [None] * BOARD_CELLS
        for index in (2, 4, 8, 14):
            state.board[index] = "tiger"
        state.board[0] = "cow"
        state.cows_placed = TOTAL_COWS
        state.cows_captured = TOTAL_COWS - 1
        state.current_turn = "tiger"

        self.assertTrue(state.select_tiger(2))
        self.assertTrue(state.move_tiger(1))
        self.assertEqual(legal_cow_moves(state.board, 0), ())

        self.assertEqual(state.winner, "tiger")
        self.assertIsNone(state.current_turn)
        self.assertTrue(state.is_over)

    def test_reset_restores_game_counts_and_four_corner_tigers(self) -> None:
        state = GameState()
        self.assertTrue(state.place(5))
        state.reset()
        self.assertEqual(state.current_turn, "cow")
        self.assertEqual(state.cows_placed, 0)
        self.assertEqual(state.cows_captured, 0)
        self.assertEqual(
            tuple(index for index, piece in enumerate(state.board) if piece == "tiger"),
            STARTING_TIGER_CELLS,
        )

    def test_current_player_can_forfeit_and_award_win_to_opponent(self) -> None:
        for player, expected_winner in (("cow", "tiger"), ("tiger", "cow")):
            with self.subTest(player=player):
                state = GameState(current_turn=player)

                self.assertTrue(state.forfeit(player))
                self.assertEqual(state.winner, expected_winner)
                self.assertEqual(state.resigned_player, player)
                self.assertIsNone(state.current_turn)
                self.assertTrue(state.is_over)

    def test_forfeit_rejects_wrong_player_or_completed_game(self) -> None:
        state = GameState()

        self.assertFalse(state.forfeit("tiger"))
        self.assertFalse(state.forfeit("unknown"))
        self.assertTrue(state.forfeit("cow"))
        self.assertFalse(state.forfeit("tiger"))

    def test_reset_clears_forfeit_result(self) -> None:
        state = GameState()
        self.assertTrue(state.forfeit("cow"))

        state.reset()

        self.assertIsNone(state.winner)
        self.assertIsNone(state.resigned_player)
        self.assertEqual(state.current_turn, "cow")


if __name__ == "__main__":
    unittest.main()
