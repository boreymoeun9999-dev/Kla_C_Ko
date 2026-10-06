export const BOARD_SIZE = 4;
export const BOARD_CELLS = BOARD_SIZE * BOARD_SIZE;
export const TOTAL_COWS = 12;
export const STARTING_TIGER_CELLS = [0, 3, 12, 15];

export function legalTigerMoves(board, index) {
  if (index < 0 || index >= BOARD_CELLS || board[index] !== "tiger") return [];
  const [row, col] = [Math.floor(index / BOARD_SIZE), index % BOARD_SIZE];
  const moves = [];
  for (const [rowDelta, colDelta] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
    const nextRow = row + rowDelta;
    const nextCol = col + colDelta;
    if (!insideBoard(nextRow, nextCol)) continue;
    const adjacent = nextRow * BOARD_SIZE + nextCol;
    if (board[adjacent] === null) {
      moves.push(adjacent);
      continue;
    }
    if (board[adjacent] !== "cow") continue;
    const landingRow = nextRow + rowDelta;
    const landingCol = nextCol + colDelta;
    if (insideBoard(landingRow, landingCol)) {
      const landing = landingRow * BOARD_SIZE + landingCol;
      if (board[landing] === null) moves.push(landing);
    }
  }
  return moves;
}

export function legalCowMoves(board, index) {
  if (index < 0 || index >= BOARD_CELLS || board[index] !== "cow") return [];
  const [row, col] = [Math.floor(index / BOARD_SIZE), index % BOARD_SIZE];
  return [[-1, 0], [1, 0], [0, -1], [0, 1]]
    .map(([dr, dc]) => [row + dr, col + dc])
    .filter(([nextRow, nextCol]) => insideBoard(nextRow, nextCol))
    .map(([nextRow, nextCol]) => nextRow * BOARD_SIZE + nextCol)
    .filter((destination) => board[destination] === null);
}

export function capturedCowCell(board, origin, destination) {
  if (
    origin < 0 || origin >= BOARD_CELLS ||
    destination < 0 || destination >= BOARD_CELLS
  ) return null;
  const originRow = Math.floor(origin / BOARD_SIZE);
  const originCol = origin % BOARD_SIZE;
  const destinationRow = Math.floor(destination / BOARD_SIZE);
  const destinationCol = destination % BOARD_SIZE;
  const rowDelta = destinationRow - originRow;
  const colDelta = destinationCol - originCol;
  if (
    Math.abs(rowDelta) + Math.abs(colDelta) !== 2 ||
    (rowDelta !== 0 && colDelta !== 0)
  ) return null;
  const middle =
    Math.floor((originRow + destinationRow) / 2) * BOARD_SIZE +
    Math.floor((originCol + destinationCol) / 2);
  return board[middle] === "cow" ? middle : null;
}

export function allTigersTrapped(board) {
  const tigerCells = board.flatMap((piece, index) => piece === "tiger" ? [index] : []);
  return tigerCells.length > 0 && tigerCells.every((index) => legalTigerMoves(board, index).length === 0);
}

export class GameState {
  constructor() {
    this.reset();
  }

  get isOver() {
    return this.winner !== null;
  }

  place(index) {
    if (
      this.isOver || this.currentTurn !== "cow" || this.cowsPlaced >= TOTAL_COWS ||
      index < 0 || index >= BOARD_CELLS || this.board[index] !== null
    ) return false;
    this.board[index] = "cow";
    this.cowsPlaced += 1;
    this.selectedTiger = null;
    this.selectedCow = null;
    if (allTigersTrapped(this.board)) {
      this.winner = this.cowCanMove() ? "cow" : "draw";
      this.currentTurn = null;
    } else {
      this.currentTurn = "tiger";
    }
    return true;
  }

  selectCow(index) {
    if (
      this.isOver || this.currentTurn !== "cow" || this.cowsPlaced < TOTAL_COWS ||
      legalCowMoves(this.board, index).length === 0
    ) return false;
    this.selectedCow = index;
    return true;
  }

  moveCow(destination) {
    const origin = this.selectedCow;
    if (
      this.isOver || this.currentTurn !== "cow" || this.cowsPlaced < TOTAL_COWS ||
      origin === null || !legalCowMoves(this.board, origin).includes(destination)
    ) return false;
    this.board[origin] = null;
    this.board[destination] = "cow";
    this.selectedCow = null;
    this.finishCowTurn();
    return true;
  }

  selectTiger(index) {
    if (
      this.isOver || this.currentTurn !== "tiger" ||
      legalTigerMoves(this.board, index).length === 0
    ) return false;
    this.selectedTiger = index;
    return true;
  }

  moveTiger(destination) {
    const origin = this.selectedTiger;
    if (
      this.isOver || this.currentTurn !== "tiger" || origin === null ||
      !legalTigerMoves(this.board, origin).includes(destination)
    ) return false;
    const captured = capturedCowCell(this.board, origin, destination);
    this.board[origin] = null;
    this.board[destination] = "tiger";
    if (captured !== null) {
      this.board[captured] = null;
      this.cowsCaptured += 1;
    }
    this.selectedTiger = null;
    this.selectedCow = null;
    if (this.cowsCaptured >= TOTAL_COWS) {
      this.winner = "tiger";
      this.currentTurn = null;
    } else if (allTigersTrapped(this.board)) {
      this.winner = this.cowCanMove() ? "cow" : "draw";
      this.currentTurn = null;
    } else if (!this.cowCanMove()) {
      this.currentTurn = "tiger";
    } else {
      this.currentTurn = "cow";
    }
    return true;
  }

  reset() {
    this.board = Array(BOARD_CELLS).fill(null);
    for (const index of STARTING_TIGER_CELLS) this.board[index] = "tiger";
    this.currentTurn = "cow";
    this.winner = null;
    this.selectedTiger = null;
    this.selectedCow = null;
    this.cowsPlaced = 0;
    this.cowsCaptured = 0;
  }

  cowCanMove() {
    if (this.cowsPlaced < TOTAL_COWS) return this.board.includes(null);
    return this.board.some(
      (piece, index) => piece === "cow" && legalCowMoves(this.board, index).length > 0,
    );
  }

  finishCowTurn() {
    if (allTigersTrapped(this.board)) {
      this.winner = this.cowCanMove() ? "cow" : "draw";
      this.currentTurn = null;
    } else {
      this.currentTurn = "tiger";
    }
  }
}

function insideBoard(row, col) {
  return row >= 0 && row < BOARD_SIZE && col >= 0 && col < BOARD_SIZE;
}
