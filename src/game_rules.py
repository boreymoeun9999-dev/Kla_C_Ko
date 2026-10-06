from collections.abc import Sequence


BOARD_SIZE = 4
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE
Board = Sequence[str | None]

STARTING_TIGER_CELLS = (0, BOARD_SIZE - 1, BOARD_CELLS - BOARD_SIZE, BOARD_CELLS - 1)


def legal_tiger_moves(board: Board, index: int) -> tuple[int, ...]:
    if index < 0 or index >= BOARD_CELLS or board[index] != "tiger":
        return ()
    row, col = divmod(index, BOARD_SIZE)
    moves = []
    for row_delta, col_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        next_row = row + row_delta
        next_col = col + col_delta
        if not (0 <= next_row < BOARD_SIZE and 0 <= next_col < BOARD_SIZE):
            continue
        adjacent = next_row * BOARD_SIZE + next_col
        if board[adjacent] is None:
            moves.append(adjacent)
            continue
        if board[adjacent] != "cow":
            continue
        landing_row = next_row + row_delta
        landing_col = next_col + col_delta
        if 0 <= landing_row < BOARD_SIZE and 0 <= landing_col < BOARD_SIZE:
            landing = landing_row * BOARD_SIZE + landing_col
            if board[landing] is None:
                moves.append(landing)
    return tuple(moves)


def legal_cow_moves(board: Board, index: int) -> tuple[int, ...]:
    if index < 0 or index >= BOARD_CELLS or board[index] != "cow":
        return ()
    row, col = divmod(index, BOARD_SIZE)
    moves = []
    for row_delta, col_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        next_row = row + row_delta
        next_col = col + col_delta
        if 0 <= next_row < BOARD_SIZE and 0 <= next_col < BOARD_SIZE:
            destination = next_row * BOARD_SIZE + next_col
            if board[destination] is None:
                moves.append(destination)
    return tuple(moves)


def captured_cow_cell(board: Board, origin: int, destination: int) -> int | None:
    if origin < 0 or origin >= BOARD_CELLS or destination < 0 or destination >= BOARD_CELLS:
        return None
    origin_row, origin_col = divmod(origin, BOARD_SIZE)
    destination_row, destination_col = divmod(destination, BOARD_SIZE)
    row_delta = destination_row - origin_row
    col_delta = destination_col - origin_col
    if abs(row_delta) + abs(col_delta) != 2 or (row_delta != 0 and col_delta != 0):
        return None
    middle = (origin_row + destination_row) // 2 * BOARD_SIZE + (
        origin_col + destination_col
    ) // 2
    return middle if board[middle] == "cow" else None


def all_tigers_trapped(board: Board) -> bool:
    tiger_cells = [index for index, piece in enumerate(board) if piece == "tiger"]
    return bool(tiger_cells) and all(not legal_tiger_moves(board, index) for index in tiger_cells)
