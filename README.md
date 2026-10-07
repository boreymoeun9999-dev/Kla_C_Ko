# Tiger vs Cow

A 4 x 4 strategy game with **4 Tigers** and **12 Cows**. Play against a friend
or choose the computer opponent on the start screen. In AI mode, choose whether
to play as Tiger or Cow. The four Tigers start automatically in the board's
corners. Tiger uses the left webcam; Cow uses the right webcam.

## Run on Windows

MediaPipe hand tracking requires a supported Python version. Use Python 3.11
and run these commands from the project folder in PowerShell:

```powershell
py -3.11 -m venv .venv-game
.\.venv-game\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-game\Scripts\python.exe main.py
```

If the `py` launcher is unavailable, use the full path to your Python 3.11
executable in the first command instead.

In VS Code, select `.venv-game\Scripts\python.exe` as the Python interpreter.

The hand-tracking model is included at `assets/models/hand_landmarker.task`. It
is the official [MediaPipe Hand Landmarker model](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task).

Connect two webcams before starting the game and allow camera access when
Windows asks. The game tries Windows camera backends and scans camera indices
0-5, assigning the first camera it finds to Tiger and the second to Cow. The
screen places Tiger's camera on the left, the board in the middle, and Cow's
camera on the right; each preview shows the camera index actually detected.
Tiger uses the left camera with the right hand, and Cow uses the right camera
with the left hand. If only one webcam is found, it is shared between both
players and shown in both previews, so both can still use camera controls.
The banner above the board clearly announces whose turn it is and which hand
to use.

If one or both webcams are missing or unavailable, that player's preview will
show that the camera is unavailable. Both players can still use the mouse:
the player whose turn it is clicks an empty square.

If the old "4 in a row" screen is still open, close it first; run the updated
game from this project folder with
`.\.venv-game\Scripts\python.exe main.py`.

## Controls

- Choose **Two players** or **Play vs AI** on the cover screen. In AI mode,
  choose **Play as Tiger** or **Play as Cow**; the computer controls the other
  side. Choose Easy (depth 1), Medium (depth 2), Hard (depth 3), or Master
  (depth 5) for the computer's search strength. The AI makes a move
  automatically when its turn starts.
- Click **Start Game**, pinch and release over it with the
  assigned hand on either camera, or press **Enter** or **Space**.
- Cow moves first. Pinch and hold, point at an empty square, then release to
  place one Cow using the **left hand only** on the right camera.
- On Tiger's turn, use the **right hand only** on the left camera to pinch and
  hold a Tiger, move your hand to an empty square,
  then release to move it one square up, down, left, or right.
- To eat a Cow, keep holding the pinch while pointing beyond an adjacent Cow
  to the empty square after it, then release.
- With the mouse, click an empty square to place a Cow. On Tiger's turn, click
  a Tiger to select it, then click an empty neighboring square or a valid
  landing square beyond a Cow to move/capture.
- The player whose turn it is can click **Forfeit turn** below the board to
  concede; the other player wins immediately.
- Change the Cambodian board design with the camera: hold only your index
  finger for Angkor Sandstone, only your middle finger for Royal Crimson,
  index and middle fingers for Emerald Lotus, or only your pinky for
  Moonstone Blue. Keep the gesture steady briefly; pinch gestures do not change
  the board.
- The turns alternate: Cow places a Cow, then Tiger moves a Tiger. After all
  12 Cows have been placed, Cow moves one Cow to an adjacent empty square on
  each turn instead of placing more Cows.
- Cow wins by trapping all four Tigers while Cow can still place a Cow.
- Tiger wins only after eating all 12 Cows; placing all 12 does not win the
  game.
- The game is a draw if Cow has no Cows left to place and no Tiger can move.
- A looping original instrumental plays during the game, alongside a short
  double-beep for Tiger and Cow moves. When either side wins, a celebratory
  instrumental plays instead and repeats for up to two minutes. Press
  **R** or click **Restart** to close the winner panel and stop the music.
- Click **Choose song** to select a WAV, OGG, or MP3 track. The game remembers
  the selected file and uses it the next time it starts.
- Click **Pause** beside the song button to pause or resume the background
  music without muting Tiger or Cow sounds.
- Click **Sound settings** to choose custom WAV, OGG, or MP3 Tiger/Cow sounds,
  use **Use default sounds** to restore the double-beep, change the game
  volume, or mute/unmute. These preferences are remembered.
- When either side wins, a congratulations panel displays the winning
  character and plays celebratory music. Successful Cow placements and Tiger
  moves play the double-beep sound. A draw has its own message and sound. No
  more Cows can be placed after all 12 have been used.
- Press **R** or click the restart button to start over.
- Press **Esc** or click the close button to quit.

Run the rules tests with:

```powershell
.\.venv-game\Scripts\python.exe -m unittest discover -s tests -v
```

## Run the browser version

Install its Node.js dependencies and start the Vite development server:

```powershell
cd web
npm install
npm run dev
```

The browser version supports mouse and touch play. Select **Enable camera** to
allow webcam hand tracking; Tiger uses the right hand and Cow uses the left.
The same webcam stream is shared between both player previews. Point your index
finger at a board square; the gold cursor shows where it is pointing. Pinch to
grab/select, move to a highlighted square, then release to make the move.
Camera access requires HTTPS outside localhost. The browser game and its
backgrounds, images, sounds, and hand-tracking model are configured as
separate Vercel services. Public paths `/backgrounds/*`, `/models/*`, `/png/*`,
and `/sounds/*` route to the static assets service; all other paths route to
the browser app.

Run the browser game tests and build with:

```powershell
npm test
npm run build
```

Use `vercel dev` from the repository root to run the services together locally.
