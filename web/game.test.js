import assert from "node:assert/strict";
import test from "node:test";
import {
  GameState,
  allTigersTrapped,
  capturedCowCell,
  legalCowMoves,
  legalTigerMoves,
} from "./game.js";

test("starts with four corner Tigers and lets Cow place first", () => {
  const game = new GameState();
  assert.deepEqual(game.board, [
    "tiger", null, null, "tiger",
    null, null, null, null,
    null, null, null, null,
    "tiger", null, null, "tiger",
  ]);
  assert.equal(game.currentTurn, "cow");
  assert.equal(game.place(5), true);
  assert.equal(game.currentTurn, "tiger");
  assert.equal(game.place(6), false);
});

test("Tiger can jump and capture an adjacent Cow", () => {
  const game = new GameState();
  game.board = [
    null, null, null, null,
    "tiger", "cow", null, null,
    null, null, null, null,
    null, null, null, null,
  ];
  game.currentTurn = "tiger";
  assert.deepEqual(legalTigerMoves(game.board, 4), [0, 8, 6]);
  assert.equal(capturedCowCell(game.board, 4, 6), 5);
  game.selectTiger(4);
  assert.equal(game.moveTiger(6), true);
  assert.equal(game.board[5], null);
  assert.equal(game.cowsCaptured, 1);
  assert.equal(game.currentTurn, "cow");
});

test("Cow can move orthogonally once all twelve are placed", () => {
  const game = new GameState();
  game.board = [
    "tiger", "cow", null, "tiger",
    null, "cow", null, null,
    null, null, null, null,
    "tiger", null, null, "tiger",
  ];
  game.currentTurn = "cow";
  game.cowsPlaced = 12;
  assert.deepEqual(legalCowMoves(game.board, 5), [9, 4, 6]);
  assert.equal(game.selectCow(5), true);
  assert.equal(game.moveCow(6), true);
  assert.equal(game.currentTurn, "tiger");
});

test("detects that all Tigers are trapped", () => {
  const board = Array(16).fill("cow");
  for (const tiger of [0, 3, 12, 15]) board[tiger] = "tiger";
  assert.equal(allTigersTrapped(board), true);
});
