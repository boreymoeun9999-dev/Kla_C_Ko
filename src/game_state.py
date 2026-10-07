from dataclasses import dataclass, field

from src.game_rules import (
    BOARD_CELLS,
    STARTING_TIGER_CELLS,
    all_tigers_trapped,
    captured_cow_cell,
    legal_cow_moves,
    legal_tiger_moves,
)

TOTAL_COWS = 12
TIGER_WIN_CAPTURES = TOTAL_COWS


def _cow_can_move(board: list[str | None], cows_placed: int) -> bool:
    if cows_placed < TOTAL_COWS:
        return any(piece is None for piece in board)
    return any(
        piece == "cow" and legal_cow_moves(board, index)
        for index, piece in enumerate(board)
    )


def _cows_are_trapped(board: list[str | None], cows_placed: int) -> bool:
    return (
        cows_placed >= TOTAL_COWS
        and any(piece == "cow" for piece in board)
        and not _cow_can_move(board, cows_placed)
    )


def _starting_board() -> list[str | None]:
    board: list[str | None] = [None] * BOARD_CELLS
    for index in STARTING_TIGER_CELLS:
        board[index] = "tiger"
    return board


@dataclass
class GameState:
    board: list[str | None] = field(default_factory=_starting_board)
    current_turn: str | None = "cow"
    winner: str | None = None
    selected_tiger: int | None = None
    selected_cow: int | None = None
    cows_placed: int = 0
    cows_captured: int = 0
    resigned_player: str | None = None

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    def place(self, index: int) -> bool:
        if (
            self.is_over
            or self.current_turn != "cow"
            or self.cows_placed >= TOTAL_COWS
            or index < 0
            or index >= BOARD_CELLS
            or self.board[index] is not None
        ):
            return False

        self.board[index] = "cow"
        self.cows_placed += 1
        self.selected_tiger = None
        self.selected_cow = None
        if all_tigers_trapped(self.board):
            self.winner = "cow"
            self.current_turn = None
        elif _cows_are_trapped(self.board, self.cows_placed):
            self.winner = "tiger"
            self.current_turn = None
        else:
            self.current_turn = "tiger"
        return True

    def select_cow(self, index: int) -> bool:
        if (
            self.is_over
            or self.current_turn != "cow"
            or self.cows_placed < TOTAL_COWS
            or not legal_cow_moves(self.board, index)
        ):
            return False
        self.selected_cow = index
        return True

    def move_cow(self, destination: int) -> bool:
        origin = self.selected_cow
        if (
            self.is_over
            or self.current_turn != "cow"
            or self.cows_placed < TOTAL_COWS
            or origin is None
            or destination not in legal_cow_moves(self.board, origin)
        ):
            return False
        self.board[origin] = None
        self.board[destination] = "cow"
        self.selected_cow = None
        if all_tigers_trapped(self.board):
            self.winner = "cow"
            self.current_turn = None
        elif _cows_are_trapped(self.board, self.cows_placed):
            self.winner = "tiger"
            self.current_turn = None
        else:
            self.current_turn = "tiger"
        return True

    def select_tiger(self, index: int) -> bool:
        if (
            self.is_over
            or self.current_turn != "tiger"
            or not legal_tiger_moves(self.board, index)
        ):
            return False
        self.selected_tiger = index
        return True

    def move_tiger(self, destination: int) -> bool:
        origin = self.selected_tiger
        if (
            self.is_over
            or self.current_turn != "tiger"
            or origin is None
            or destination not in legal_tiger_moves(self.board, origin)
        ):
            return False
        captured_cell = captured_cow_cell(self.board, origin, destination)
        self.board[origin] = None
        self.board[destination] = "tiger"
        if captured_cell is not None:
            self.board[captured_cell] = None
            self.cows_captured += 1
        self.selected_tiger = None
        self.selected_cow = None
        if self.cows_captured >= TIGER_WIN_CAPTURES:
            self.winner = "tiger"
            self.current_turn = None
        elif all_tigers_trapped(self.board):
            self.winner = "cow"
            self.current_turn = None
        elif _cows_are_trapped(self.board, self.cows_placed):
            self.winner = "tiger"
            self.current_turn = None
        elif not _cow_can_move(self.board, self.cows_placed):
            self.current_turn = "tiger"
        else:
            self.current_turn = "cow"
        return True

    def forfeit(self, player: str) -> bool:
        if (
            self.is_over
            or player not in {"tiger", "cow"}
            or player != self.current_turn
        ):
            return False

        self.winner = "cow" if player == "tiger" else "tiger"
        self.resigned_player = player
        self.current_turn = None
        self.selected_tiger = None
        self.selected_cow = None
        return True

    def reset(self) -> None:
        self.board = _starting_board()
        self.current_turn = "cow"
        self.winner = None
        self.selected_tiger = None
        self.selected_cow = None
        self.cows_placed = 0
        self.cows_captured = 0
        self.resigned_player = None
