from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import random

from src.game_rules import legal_cow_moves, legal_tiger_moves
from src.game_state import GameState, TOTAL_COWS


AI_DIFFICULTIES = {
    "Easy": 1,
    "Medium": 2,
    "Hard": 3,
    "Master": 5,
}

# Represent a move by its player, origin cell, and destination cell.
@dataclass(frozen=True)
class _Move:
    player: str
    origin: int | None
    destination: int


# Generate all legal moves for the player whose turn it is.
def _legal_moves(state: GameState, player: str) -> list[_Move]:
    if player == "cow" and state.cows_placed < TOTAL_COWS:
        return [
            _Move(player, None, index)
            for index, piece in enumerate(state.board)
            if piece is None
        ]

    moves = []
    for index, piece in enumerate(state.board):
        if piece != player:
            continue
        destinations = (
            legal_cow_moves(state.board, index)
            if player == "cow"
            else legal_tiger_moves(state.board, index)
        )
        moves.extend(_Move(player, index, destination) for destination in destinations)
    return moves


# Apply a move to a copied state using the game's regular rules.
def _apply_move(state: GameState, move: _Move) -> bool:
    if move.player == "cow" and move.origin is None:
        return state.place(move.destination)

    if move.origin is None:
        return False
    if move.player == "cow":
        return state.select_cow(move.origin) and state.move_cow(move.destination)
    return state.select_tiger(move.origin) and state.move_tiger(move.destination)


# Score how favorable the board is for the tigers or cows.
def _evaluate(state: GameState, player: str) -> int:
    if state.winner is not None:
        if state.winner == "draw":
            return 0
        return 1_000_000 if state.winner == player else -1_000_000

    tiger_moves = sum(
        len(legal_tiger_moves(state.board, index))
        for index, piece in enumerate(state.board)
        if piece == "tiger"
    )
    cow_moves = sum(
        len(legal_cow_moves(state.board, index))
        for index, piece in enumerate(state.board)
        if piece == "cow"
    )
    if state.cows_placed < TOTAL_COWS:
        cow_moves += sum(piece is None for piece in state.board)

    tiger_score = state.cows_captured * 30 + tiger_moves * 2 - cow_moves
    return tiger_score if player == "tiger" else -tiger_score


# Search future moves; alpha-beta pruning skips branches that cannot improve the result.
def _search(
    state: GameState,
    player: str,
    depth: int,
    alpha: float,
    beta: float,
) -> int:
    if state.is_over or depth == 0:
        return _evaluate(state, player)

    turn = state.current_turn
    if turn not in {"tiger", "cow"}:
        return _evaluate(state, player)
    moves = _legal_moves(state, turn)
    if not moves:
        return _evaluate(state, player)

    maximizing = turn == player
    best_score = float("-inf") if maximizing else float("inf")
    for move in moves:
        candidate = deepcopy(state)
        if not _apply_move(candidate, move):
            continue
        score = _search(candidate, player, depth - 1, alpha, beta)
        if maximizing:
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
        else:
            best_score = min(best_score, score)
            beta = min(beta, best_score)
        if beta <= alpha:
            break
    return int(best_score)


# Choose the highest-scoring move within the requested search depth.
def play_ai_turn(state: GameState, depth: int = 1) -> bool:
    player = state.current_turn
    if (
        state.is_over
        or player not in {"tiger", "cow"}
        or depth < 1
    ):
        return False

    moves = _legal_moves(state, player)
    if not moves:
        return False

    scored_moves: list[tuple[int, _Move]] = []
    for move in moves:
        candidate = deepcopy(state)
        if _apply_move(candidate, move):
            score = _search(
                candidate,
                player,
                depth - 1,
                float("-inf"),
                float("inf"),
            )
            scored_moves.append((score, move))
    if not scored_moves:
        return False

    best_score = max(score for score, _ in scored_moves)
    best_moves = [move for score, move in scored_moves if score == best_score]
    return _apply_move(state, random.choice(best_moves))
