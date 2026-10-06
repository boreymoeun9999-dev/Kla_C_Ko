import {
  GameState,
  TOTAL_COWS,
  legalCowMoves,
  legalTigerMoves,
} from "./game.js";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import "./style.css";

const game = new GameState();
const boardElement = document.querySelector("#board");
const cover = document.querySelector("#cover");
const gameElement = document.querySelector("#game");
const turnBanner = document.querySelector("#turn-banner");
const gameMessage = document.querySelector("#game-message");
const cameraToggle = document.querySelector("#camera-toggle");
const cameraStatus = document.querySelector("#camera-status");
const handCursor = document.querySelector("#hand-cursor");
const videoElements = [
  document.querySelector("#camera-preview-tiger"),
  document.querySelector("#camera-preview-cow"),
];
const moveSound = document.querySelector("#move-sound");
const music = document.querySelector("#music");
const volume = document.querySelector("#volume");
const muted = document.querySelector("#mute-toggle");
const winnerDialog = document.querySelector("#winner-dialog");
const winnerTitle = document.querySelector("#winner-title");
const winnerCopy = document.querySelector("#winner-copy");
const winnerImage = document.querySelector("#winner-image");
const handCanvas = document.createElement("canvas");
const handContext = handCanvas.getContext("2d", { willReadFrequently: false });
let handLandmarker = null;
let cameraStream = null;
let animationFrame = 0;
let lastVideoTime = -1;
let pinching = false;
let currentCursor = null;

function render() {
  boardElement.replaceChildren();
  const activeMoves = game.currentTurn === "tiger"
    ? game.selectedTiger === null ? [] : legalTigerMoves(game.board, game.selectedTiger)
    : game.selectedCow === null ? [] : legalCowMoves(game.board, game.selectedCow);

  game.board.forEach((piece, index) => {
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = `cell ${(Math.floor(index / 4) + index % 4) % 2 ? "dark" : "light"}`;
    cell.setAttribute("role", "gridcell");
    cell.setAttribute("aria-label", cellLabel(index, piece));
    if (activeMoves.includes(index)) cell.classList.add("destination");
    if (index === game.selectedTiger || index === game.selectedCow) {
      cell.classList.add("selected");
    }
    if (piece) {
      const image = document.createElement("img");
      image.src = `/png/${piece}_face.png`;
      image.alt = piece === "tiger" ? "Tiger" : "Cow";
      image.draggable = false;
      cell.append(image);
    }
    cell.addEventListener("click", () => handleCell(index));
    boardElement.append(cell);
  });

  document.querySelector("#placed-count").textContent = game.cowsPlaced;
  document.querySelector("#captured-count").textContent = game.cowsCaptured;
  document.querySelector("#cow-help").textContent = game.cowsPlaced < TOTAL_COWS
    ? `Place ${TOTAL_COWS - game.cowsPlaced} more Cow${TOTAL_COWS - game.cowsPlaced === 1 ? "" : "s"} to trap the Tigers.`
    : "Select a Cow, then move it to an adjacent empty square.";

  if (game.winner) {
    turnBanner.textContent = game.winner === "draw"
      ? "Draw - neither side can move."
      : `${capitalize(game.winner)} wins!`;
    showWinner();
  } else if (game.currentTurn) {
    turnBanner.textContent = `${capitalize(game.currentTurn)}'s turn`;
    gameMessage.textContent = game.currentTurn === "cow"
      ? game.cowsPlaced < TOTAL_COWS
        ? "Select an empty square to place a Cow."
        : "Select one of your Cows, then an adjacent empty square."
      : "Select a Tiger, then a highlighted destination.";
  }
}

function handleCell(index) {
  if (game.isOver) return;
  const player = game.currentTurn;
  let changed = false;
  if (player === "cow") {
    if (game.cowsPlaced < TOTAL_COWS) {
      changed = game.place(index);
    } else if (game.selectedCow === null || game.board[index] === "cow") {
      changed = game.selectCow(index);
    } else {
      changed = game.moveCow(index);
    }
  } else if (player === "tiger") {
    if (game.selectedTiger === null || game.board[index] === "tiger") {
      changed = game.selectTiger(index);
    } else {
      changed = game.moveTiger(index);
    }
  }
  if (changed) playMoveSound(player);
  render();
}

function moveAtNormalizedPosition(x, y) {
  const rect = boardElement.getBoundingClientRect();
  if (x < 0 || x > 1 || y < 0 || y > 1) {
    currentCursor = null;
    handCursor.classList.add("hidden");
    document.querySelectorAll(".cell.gesture-hover").forEach((cell) => {
      cell.classList.remove("gesture-hover");
    });
    return;
  }
  const index = Math.min(3, Math.floor(y * 4)) * 4 + Math.min(3, Math.floor(x * 4));
  currentCursor = { x: rect.left + x * rect.width, y: rect.top + y * rect.height };
  const sectionRect = boardElement.parentElement.getBoundingClientRect();
  handCursor.style.left = `${currentCursor.x - sectionRect.left}px`;
  handCursor.style.top = `${currentCursor.y - sectionRect.top}px`;
  handCursor.classList.remove("hidden");
  document.querySelectorAll(".cell.gesture-hover").forEach((cell) => {
    cell.classList.remove("gesture-hover");
  });
  boardElement.children[index]?.classList.add("gesture-hover");
}

function commitGesture(x, y) {
  moveAtNormalizedPosition(x, y);
  if (!currentCursor) return;
  const rect = boardElement.getBoundingClientRect();
  const index = Math.min(3, Math.floor(y * 4)) * 4 + Math.min(3, Math.floor(x * 4));
  if (
    x >= 0 && x <= 1 && y >= 0 && y <= 1 &&
    currentCursor.x >= rect.left && currentCursor.x <= rect.right &&
    currentCursor.y >= rect.top && currentCursor.y <= rect.bottom
  ) handleCell(index);
}

async function toggleCamera() {
  if (cameraStream) {
    stopCamera();
    return;
  }
  cameraToggle.disabled = true;
  cameraStatus.textContent = "Requesting camera permission…";
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
    });
    for (const video of videoElements) {
      video.srcObject = cameraStream;
      await video.play();
      video.closest(".camera-frame").classList.add("active");
    }
    cameraStatus.textContent = "Loading hand tracking…";
    handLandmarker = await createHandLandmarker();
    cameraStatus.textContent =
      "One camera feed is shared. Use your right hand for Tiger and left hand for Cow.";
    cameraToggle.textContent = "Disable camera";
    pinching = false;
    animationFrame = requestAnimationFrame(processCameraFrame);
  } catch (error) {
    stopCamera();
    cameraStatus.textContent = `Camera unavailable: ${error.message}`;
  } finally {
    cameraToggle.disabled = false;
  }
}

async function createHandLandmarker() {
  const fileset = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm",
  );
  return HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: "/models/hand_landmarker.task" },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.6,
    minHandPresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
}

function processCameraFrame() {
  if (!cameraStream || !handLandmarker) return;
  const video = videoElements[0];
  if (
    video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
    video.currentTime !== lastVideoTime
  ) {
    lastVideoTime = video.currentTime;
    handCanvas.width = video.videoWidth;
    handCanvas.height = video.videoHeight;
    handContext.save();
    handContext.translate(handCanvas.width, 0);
    handContext.scale(-1, 1);
    handContext.drawImage(video, 0, 0, handCanvas.width, handCanvas.height);
    handContext.restore();

    const result = handLandmarker.detectForVideo(handCanvas, performance.now());
    const preferredHand = game.currentTurn === "tiger" ? "Right" : "Left";
    const handIndex = result.handedness?.findIndex(
      (classification) => classification[0]?.categoryName === preferredHand,
    ) ?? -1;
    if (handIndex >= 0 && result.landmarks?.[handIndex]) {
      const landmarks = result.landmarks[handIndex];
      const thumb = landmarks[4];
      const finger = landmarks[8];
      const pinchingNow = Math.hypot(thumb.x - finger.x, thumb.y - finger.y) < 0.045;
      moveAtNormalizedPosition(finger.x, finger.y);
      if (pinching && !pinchingNow) commitGesture(finger.x, finger.y);
      pinching = pinchingNow;
    } else {
      pinching = false;
      currentCursor = null;
      handCursor.classList.add("hidden");
      document.querySelectorAll(".cell.gesture-hover").forEach((cell) => {
        cell.classList.remove("gesture-hover");
      });
    }
  }
  animationFrame = requestAnimationFrame(processCameraFrame);
}

function stopCamera() {
  cancelAnimationFrame(animationFrame);
  animationFrame = 0;
  if (cameraStream) {
    for (const track of cameraStream.getTracks()) track.stop();
    cameraStream = null;
  }
  if (handLandmarker) {
    handLandmarker.close();
    handLandmarker = null;
  }
  for (const video of videoElements) {
    video.srcObject = null;
    video.closest(".camera-frame").classList.remove("active");
  }
  cameraToggle.textContent = "Enable camera";
  cameraStatus.textContent = "Camera off. Mouse and touch are always available.";
  pinching = false;
  currentCursor = null;
  handCursor.classList.add("hidden");
}

function showWinner() {
  winnerTitle.textContent = game.winner === "draw"
    ? "It's a draw!"
    : `Congratulations, ${capitalize(game.winner)}!`;
  winnerCopy.textContent = game.winner === "cow"
    ? "All four Tigers are trapped."
    : game.winner === "tiger"
      ? "All twelve Cows have been captured."
      : "Neither side can make a move.";
  winnerImage.hidden = game.winner === "draw";
  if (game.winner !== "draw") winnerImage.src = `/png/${game.winner}_face.png`;
  if (!winnerDialog.open) winnerDialog.showModal();
}

function playMoveSound(player) {
  if (muted.getAttribute("aria-pressed") === "true") return;
  moveSound.src = `/sounds/${player === "tiger" ? "tiger-roar" : "cow-moo"}.mp3`;
  moveSound.volume = Number(volume.value) / 100;
  moveSound.currentTime = 0;
  moveSound.play().catch((error) => {
    gameMessage.textContent = `Could not play move sound: ${error.message}`;
  });
}

function cellLabel(index, piece) {
  const place = `row ${Math.floor(index / 4) + 1}, column ${index % 4 + 1}`;
  return piece ? `${capitalize(piece)} at ${place}` : `Empty ${place}`;
}

function capitalize(value) {
  return value[0].toUpperCase() + value.slice(1);
}

document.querySelector("#start-game").addEventListener("click", () => {
  cover.classList.add("hidden");
  gameElement.classList.remove("hidden");
});

document.querySelector("#restart").addEventListener("click", () => {
  game.reset();
  winnerDialog.close();
  render();
});

document.querySelector("#play-again").addEventListener("click", () => {
  game.reset();
  winnerDialog.close();
  render();
});

cameraToggle.addEventListener("click", toggleCamera);
document.querySelector("#music-file").addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  music.src = URL.createObjectURL(file);
  music.play().catch((error) => {
    cameraStatus.textContent = `Could not play selected song: ${error.message}`;
  });
  document.querySelector("#music-toggle").disabled = false;
});

document.querySelector("#music-toggle").addEventListener("click", (event) => {
  if (music.paused) {
    music.play().catch((error) => {
      cameraStatus.textContent = `Could not play selected song: ${error.message}`;
    });
    event.currentTarget.textContent = "Pause";
  } else {
    music.pause();
    event.currentTarget.textContent = "Play";
  }
});

muted.addEventListener("click", () => {
  const next = muted.getAttribute("aria-pressed") !== "true";
  muted.setAttribute("aria-pressed", String(next));
  muted.textContent = next ? "Unmute" : "Mute";
});

volume.addEventListener("input", () => {
  moveSound.volume = Number(volume.value) / 100;
  music.volume = Number(volume.value) / 100;
});

moveSound.volume = Number(volume.value) / 100;
music.volume = Number(volume.value) / 100;

document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "r" && !cover.classList.contains("hidden")) return;
  if (event.key.toLowerCase() === "r" && !gameElement.classList.contains("hidden")) {
    game.reset();
    winnerDialog.close();
    render();
  }
});

window.addEventListener("beforeunload", () => {
  stopCamera();
  if (music.src.startsWith("blob:")) URL.revokeObjectURL(music.src);
});

render();
