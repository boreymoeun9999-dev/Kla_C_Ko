// Port of src/game_rules.py and src/game_state.py.

export const BOARD_SIZE = 4;
export const BOARD_CELLS = BOARD_SIZE * BOARD_SIZE;
export const STARTING_TIGER_CELLS = [0, BOARD_SIZE - 1, BOARD_CELLS - BOARD_SIZE, BOARD_CELLS - 1];
export const TOTAL_COWS = 12;
export const TIGER_WIN_CAPTURES = TOTAL_COWS;

const DIRECTIONS = [[-1, 0], [1, 0], [0, -1], [0, 1]];
const onBoard = (row, col) => row >= 0 && row < BOARD_SIZE && col >= 0 && col < BOARD_SIZE;

export function legalTigerMoves(board, index) {
  if (index == null || index < 0 || index >= BOARD_CELLS || board[index] !== "tiger") return [];
  const row = Math.floor(index / BOARD_SIZE);
  const col = index % BOARD_SIZE;
  const moves = [];
  for (const [dr, dc] of DIRECTIONS) {
    const nextRow = row + dr;
    const nextCol = col + dc;
    if (!onBoard(nextRow, nextCol)) continue;
    const adjacent = nextRow * BOARD_SIZE + nextCol;
    if (board[adjacent] === null) {
      moves.push(adjacent);
      continue;
    }
    if (board[adjacent] !== "cow") continue;
    const landingRow = nextRow + dr;
    const landingCol = nextCol + dc;
    if (onBoard(landingRow, landingCol)) {
      const landing = landingRow * BOARD_SIZE + landingCol;
      if (board[landing] === null) moves.push(landing);
    }
  }
  return moves;
}

export function legalCowMoves(board, index) {
  if (index == null || index < 0 || index >= BOARD_CELLS || board[index] !== "cow") return [];
  const row = Math.floor(index / BOARD_SIZE);
  const col = index % BOARD_SIZE;
  const moves = [];
  for (const [dr, dc] of DIRECTIONS) {
    const nextRow = row + dr;
    const nextCol = col + dc;
    if (onBoard(nextRow, nextCol)) {
      const destination = nextRow * BOARD_SIZE + nextCol;
      if (board[destination] === null) moves.push(destination);
    }
  }
  return moves;
}

export function capturedCowCell(board, origin, destination) {
  if (origin < 0 || origin >= BOARD_CELLS || destination < 0 || destination >= BOARD_CELLS) return null;
  const originRow = Math.floor(origin / BOARD_SIZE);
  const originCol = origin % BOARD_SIZE;
  const destRow = Math.floor(destination / BOARD_SIZE);
  const destCol = destination % BOARD_SIZE;
  const dr = destRow - originRow;
  const dc = destCol - originCol;
  if (Math.abs(dr) + Math.abs(dc) !== 2 || (dr !== 0 && dc !== 0)) return null;
  const middle = ((originRow + destRow) / 2) * BOARD_SIZE + (originCol + destCol) / 2;
  return board[middle] === "cow" ? middle : null;
}

export function allTigersTrapped(board) {
  const tigers = board.flatMap((piece, index) => (piece === "tiger" ? [index] : []));
  return tigers.length > 0 && tigers.every((index) => legalTigerMoves(board, index).length === 0);
}

function cowCanMove(board, cowsPlaced) {
  if (cowsPlaced < TOTAL_COWS) return board.some((piece) => piece === null);
  return board.some((piece, index) => piece === "cow" && legalCowMoves(board, index).length > 0);
}

function startingBoard() {
  const board = Array(BOARD_CELLS).fill(null);
  for (const index of STARTING_TIGER_CELLS) board[index] = "tiger";
  return board;
}

export class GameState {
  constructor() {
    this.reset();
  }

  get isOver() {
    return this.winner !== null;
  }

  reset() {
    this.board = startingBoard();
    this.currentTurn = "cow";
    this.winner = null;
    this.selectedTiger = null;
    this.selectedCow = null;
    this.cowsPlaced = 0;
    this.cowsCaptured = 0;
  }

  #finishCowTurn() {
    if (allTigersTrapped(this.board)) {
      this.winner = cowCanMove(this.board, this.cowsPlaced) ? "cow" : "draw";
      this.currentTurn = null;
    } else {
      this.currentTurn = "tiger";
    }
  }

  place(index) {
    if (
      this.isOver ||
      this.currentTurn !== "cow" ||
      this.cowsPlaced >= TOTAL_COWS ||
      index < 0 ||
      index >= BOARD_CELLS ||
      this.board[index] !== null
    ) {
      return false;
    }
    this.board[index] = "cow";
    this.cowsPlaced += 1;
    this.selectedTiger = null;
    this.selectedCow = null;
    this.#finishCowTurn();
    return true;
  }

  selectCow(index) {
    if (
      this.isOver ||
      this.currentTurn !== "cow" ||
      this.cowsPlaced < TOTAL_COWS ||
      legalCowMoves(this.board, index).length === 0
    ) {
      return false;
    }
    this.selectedCow = index;
    return true;
  }

  moveCow(destination) {
    const origin = this.selectedCow;
    if (
      this.isOver ||
      this.currentTurn !== "cow" ||
      this.cowsPlaced < TOTAL_COWS ||
      origin === null ||
      !legalCowMoves(this.board, origin).includes(destination)
    ) {
      return false;
    }
    this.board[origin] = null;
    this.board[destination] = "cow";
    this.selectedCow = null;
    this.#finishCowTurn();
    return true;
  }

  selectTiger(index) {
    if (this.isOver || this.currentTurn !== "tiger" || legalTigerMoves(this.board, index).length === 0) {
      return false;
    }
    this.selectedTiger = index;
    return true;
  }

  moveTiger(destination) {
    const origin = this.selectedTiger;
    if (
      this.isOver ||
      this.currentTurn !== "tiger" ||
      origin === null ||
      !legalTigerMoves(this.board, origin).includes(destination)
    ) {
      return false;
    }
    const captured = capturedCowCell(this.board, origin, destination);
    this.board[origin] = null;
    this.board[destination] = "tiger";
    if (captured !== null) {
      this.board[captured] = null;
      this.cowsCaptured += 1;
    }
    this.selectedTiger = null;
    this.selectedCow = null;
    if (this.cowsCaptured >= TIGER_WIN_CAPTURES) {
      this.winner = "tiger";
      this.currentTurn = null;
    } else if (allTigersTrapped(this.board)) {
      this.winner = cowCanMove(this.board, this.cowsPlaced) ? "cow" : "draw";
      this.currentTurn = null;
    } else if (!cowCanMove(this.board, this.cowsPlaced)) {
      this.currentTurn = "tiger";
    } else {
      this.currentTurn = "cow";
    }
    return true;
  }
}
