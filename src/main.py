from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pygame
from cv2.typing import MatLike
from tkinter import Tk, filedialog

from src.camera import Camera, open_player_cameras
from src.config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from src.game_state import GameState, TOTAL_COWS
from src.game_rules import legal_cow_moves, legal_tiger_moves
from src.gesture_recognizer import GestureRecognizer, HandInput, map_to_board
from src.hand_tracker import HandObservation, HandTracker
from src.renderer import Renderer
from src.sound_effects import SAMPLE_RATE, SoundEffects


PLAYERS = ("tiger", "cow")
PLAYER_HANDS = {"tiger": "right", "cow": "left"}


class _ClickRenderer(Protocol):
    def cell_at(self, position: tuple[int, int]) -> int | None: ...


class _ClickSounds(Protocol):
    def play_player(self, player: str) -> None: ...
    def play_winner(self, winner: str) -> None: ...
    def play_draw(self) -> None: ...


def main() -> None:
    pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=1)
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Tiger vs Cow")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    sounds = SoundEffects()
    state = GameState()
    gestures = {player: GestureRecognizer() for player in PLAYERS}
    cameras, camera_messages = open_player_cameras(PLAYERS)
    camera_indices = {
        player: camera.device_index if camera is not None else None
        for player, camera in cameras.items()
    }
    camera_frames: dict[str, MatLike | None] = {player: None for player in PLAYERS}

    trackers: dict[str, HandTracker | None] = {player: None for player in PLAYERS}
    trackers_by_camera: dict[int, HandTracker] = {}
    try:
        for player in PLAYERS:
            camera = cameras[player]
            if camera is None:
                continue
            tracker = trackers_by_camera.get(camera.device_index)
            if tracker is None:
                tracker = HandTracker()
                trackers_by_camera[camera.device_index] = tracker
            trackers[player] = tracker
    except (FileNotFoundError, RuntimeError) as error:
        for tracker in trackers_by_camera.values():
            tracker.close()
        closed_cameras = set()
        for player, camera in cameras.items():
            if camera is not None and id(camera) not in closed_cameras:
                camera.close()
                closed_cameras.add(id(camera))
            cameras[player] = None
            camera_messages[player] = str(error)
        trackers = {player: None for player in PLAYERS}
        trackers_by_camera = {}

    running = True
    game_started = False
    try:
        if sounds.music_path is not None:
            renderer.music_label = sounds.music_path.name
        renderer.sound_volume = sounds.volume
        renderer.sound_muted = sounds.muted
        renderer.music_paused = sounds.music_paused
        renderer.player_sound_labels.update(
            {player: path.name for player, path in sounds.player_sound_paths.items()}
        )
        if renderer.active_name_field is not None:
            pygame.key.start_text_input()
        while running:
            sounds.update()
            renderer.sound_volume = sounds.volume
            renderer.sound_muted = sounds.muted
            if not game_started:
                camera_started = False
                camera_cursor = None
                start_events = pygame.event.get()
                has_text_input = any(
                    event.type == pygame.TEXTINPUT for event in start_events
                )
                for event in start_events:
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif (
                            event.key in (pygame.K_RETURN, pygame.K_SPACE)
                            and renderer.active_name_field is None
                        ):
                            game_started = True
                            sounds.start_music()
                        else:
                            had_active_name_field = renderer.active_name_field is not None
                            renderer.handle_name_input(
                                event,
                                allow_key_text=not has_text_input,
                            )
                            if (
                                had_active_name_field
                                and renderer.active_name_field is None
                            ):
                                pygame.key.stop_text_input()
                    elif event.type == pygame.TEXTINPUT:
                        renderer.handle_name_input(event)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        had_active_name_field = renderer.active_name_field is not None
                        if renderer.focus_name_field(event.pos):
                            if (
                                not had_active_name_field
                                or renderer.active_name_field is not None
                            ):
                                pygame.key.start_text_input()
                            continue
                        if had_active_name_field:
                            pygame.key.stop_text_input()
                        if renderer.start_button_rect.collidepoint(event.pos):
                            game_started = True
                            sounds.start_music()

                if not game_started:
                    camera_started, camera_cursor = _camera_clicked_start(
                        cameras, trackers, gestures, renderer.start_button_rect
                    )
                    if camera_started:
                        if renderer.active_name_field is not None:
                            pygame.key.stop_text_input()
                        game_started = True
                        sounds.start_music()

                renderer.draw_start_screen(camera_cursor)
                pygame.display.flip()
                clock.tick(FPS)
                continue

            cursor = None
            gestures_this_frame = {}
            gesture_positions = {}
            active_player = state.current_turn
            frames_by_camera: dict[int, MatLike | None] = {}
            hands_by_camera = {}
            for player in PLAYERS:
                camera = cameras[player]
                tracker = trackers[player]
                if camera is None:
                    gestures[player].update(None)
                    continue
                device_index = camera.device_index
                if device_index not in frames_by_camera:
                    frame = camera.read()
                    if frame is None:
                        camera.close()
                        for aliased_player, aliased_camera in cameras.items():
                            if aliased_camera is camera:
                                cameras[aliased_player] = None
                                camera_frames[aliased_player] = None
                                camera_messages[aliased_player] = (
                                    f"{aliased_player.title()} camera stopped. "
                                    "Mouse control is available."
                                )
                                gestures[aliased_player].update(None)
                        frames_by_camera[device_index] = None
                        hands_by_camera[device_index] = None
                        continue
                    frames_by_camera[device_index] = frame
                    hands_by_camera[device_index] = (
                        tracker.process(frame) if tracker is not None else None
                    )
                frame = frames_by_camera[device_index]
                if frame is None:
                    gestures[player].update(None)
                    continue

                camera_frames[player] = frame
                hand = _hand_input_for_player(
                    player,
                    hands_by_camera[device_index],
                )
                normalized_cursor, gesture_click = gestures[player].update(hand)
                gestures_this_frame[player] = gesture_click
                if normalized_cursor is not None:
                    gesture_positions[player] = normalized_cursor

            if active_player is not None:
                hand_position = gesture_positions.get(active_player)
                if hand_position is not None:
                    cursor = map_to_board(
                        hand_position,
                        renderer.board_rect.left,
                        renderer.board_rect.top,
                        renderer.board_rect.width,
                        renderer.board_rect.height,
                    )
                if (
                    not renderer.sound_settings_open
                    and gestures_this_frame.get(active_player, False)
                    and cursor is not None
                ):
                    _handle_click(active_player, cursor, state, renderer, sounds)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if renderer.sound_settings_open:
                            renderer.sound_settings_open = False
                        else:
                            running = False
                    elif event.key == pygame.K_r and not renderer.sound_settings_open:
                        sounds.stop_winner()
                        state.reset()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if renderer.sound_settings_open:
                        _handle_sound_settings_click(
                            event.pos, renderer, sounds
                        )
                    elif renderer.home_rect.collidepoint(event.pos):
                        sounds.stop_winner()
                        state.reset()
                        game_started = False
                        renderer.focus_name_field(
                            renderer.name_field_rects["tiger"].center
                        )
                        pygame.key.start_text_input()
                    elif renderer.sound_settings_rect.collidepoint(event.pos):
                        renderer.sound_settings_open = True
                    elif renderer.music_toggle_rect.collidepoint(event.pos):
                        sounds.toggle_music()
                        renderer.music_paused = sounds.music_paused
                    elif renderer.close_rect.collidepoint(event.pos):
                        running = False
                    elif renderer.restart_rect.collidepoint(event.pos):
                        sounds.stop_winner()
                        state.reset()
                    elif renderer.music_rect.collidepoint(event.pos):
                        music_path = _choose_music_file()
                        if music_path is not None:
                            try:
                                sounds.set_music(music_path)
                                renderer.music_label = music_path.name
                            except (pygame.error, OSError) as error:
                                renderer.music_label = "Song error"
                                print(f"Could not load selected music: {error}")
                    else:
                        _handle_click(
                            state.current_turn, event.pos, state, renderer, sounds
                        )

            renderer.draw(state, cursor, camera_frames, camera_messages, camera_indices)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        sounds.stop_music()
        for tracker in trackers_by_camera.values():
            tracker.close()
        seen_cameras = set()
        for camera in cameras.values():
            if camera is not None and id(camera) not in seen_cameras:
                camera.close()
                seen_cameras.add(id(camera))
        pygame.quit()


def _handle_click(
    player: str | None,
    position: tuple[int, int],
    state: GameState,
    renderer: _ClickRenderer,
    sounds: _ClickSounds,
) -> None:
    if player is None or state.is_over:
        return
    cell = renderer.cell_at(position)
    if cell is None:
        return
    if player == "cow":
        if state.cows_placed < TOTAL_COWS:
            if state.place(cell):
                if state.winner is not None:
                    _play_action_sound(state, sounds)
                else:
                    sounds.play_player("cow")
            return
        if state.selected_cow is None or state.board[cell] == "cow":
            if state.select_cow(cell):
                sounds.play_player("cow")
            return
        if cell in legal_cow_moves(state.board, state.selected_cow):
            if state.move_cow(cell):
                if state.winner is not None:
                    _play_action_sound(state, sounds)
                else:
                    sounds.play_player("cow")
        return

    if state.selected_tiger is None or state.board[cell] == "tiger":
        if state.select_tiger(cell):
            sounds.play_player("tiger")
        return
    if cell in legal_tiger_moves(state.board, state.selected_tiger):
        if state.move_tiger(cell):
            if state.winner is not None:
                _play_action_sound(state, sounds)
            else:
                sounds.play_player("tiger")


def _camera_clicked_start(
    cameras: dict[str, Camera | None],
    trackers: dict[str, HandTracker | None],
    gestures: dict[str, GestureRecognizer],
    start_button_rect: pygame.Rect,
) -> tuple[bool, tuple[int, int] | None]:
    frames_by_camera: dict[int, MatLike | None] = {}
    hands_by_camera: dict[int, HandObservation | None] = {}
    cursor = None

    for player in PLAYERS:
        camera = cameras[player]
        if camera is None:
            gestures[player].update(None)
            continue

        device_index = camera.device_index
        if device_index not in frames_by_camera:
            frame = camera.read()
            if frame is None:
                camera.close()
                for aliased_player, aliased_camera in cameras.items():
                    if aliased_camera is camera:
                        cameras[aliased_player] = None
                        gestures[aliased_player].update(None)
                frames_by_camera[device_index] = None
                hands_by_camera[device_index] = None
            else:
                frames_by_camera[device_index] = frame
                tracker = trackers[player]
                hands_by_camera[device_index] = (
                    tracker.process(frame) if tracker is not None else None
                )

        if frames_by_camera[device_index] is None:
            gestures[player].update(None)
            continue

        hand = _hand_input_for_player(player, hands_by_camera[device_index])
        normalized_cursor, gesture_click = gestures[player].update(hand)
        if normalized_cursor is None:
            continue
        cursor = map_to_board(
            normalized_cursor,
            0,
            0,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )
        if gesture_click and start_button_rect.collidepoint(cursor):
            return True, cursor

    return False, cursor


def _choose_music_file() -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected_path = filedialog.askopenfilename(
            title="Choose game music",
            filetypes=(
                ("Music files", "*.wav *.ogg *.mp3"),
                ("All files", "*.*"),
            ),
        )
    finally:
        root.destroy()
    return Path(selected_path) if selected_path else None


def _choose_player_sound(player: str) -> Path | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected_path = filedialog.askopenfilename(
            title=f"Choose {player} sound",
            filetypes=(
                ("Sound files", "*.wav *.ogg *.mp3"),
                ("All files", "*.*"),
            ),
        )
    finally:
        root.destroy()
    return Path(selected_path) if selected_path else None


def _handle_sound_settings_click(
    position: tuple[int, int],
    renderer: Renderer,
    sounds: SoundEffects,
) -> None:
    player: str | None = None
    if renderer.settings_close_rect.collidepoint(position):
        renderer.sound_settings_open = False
        return
    elif renderer.settings_volume_down_rect.collidepoint(position):
        sounds.set_volume(sounds.volume - 0.1)
        return
    elif renderer.settings_volume_up_rect.collidepoint(position):
        sounds.set_volume(sounds.volume + 0.1)
        return
    elif renderer.settings_mute_rect.collidepoint(position):
        sounds.toggle_mute()
        return
    elif renderer.settings_tiger_rect.collidepoint(position):
        player = "tiger"
    elif renderer.settings_cow_rect.collidepoint(position):
        player = "cow"
    else:
        return

    if player is None:
        return
    sound_path = _choose_player_sound(player)
    if sound_path is None:
        return
    try:
        sounds.set_player_sound(player, sound_path)
        renderer.player_sound_labels[player] = sound_path.name
    except (pygame.error, OSError, ValueError) as error:
        renderer.player_sound_labels[player] = "Load error"
        print(f"Could not load selected {player} sound: {error}")


def _play_action_sound(state: GameState, sounds: _ClickSounds) -> None:
    if state.winner == "draw":
        sounds.play_draw()
    elif state.winner is not None:
        sounds.play_winner(state.winner)


def _hand_input_for_player(
    player: str,
    observation: HandObservation | None,
) -> HandInput:
    if (
        observation is None
        or observation.handedness.casefold() != PLAYER_HANDS[player]
    ):
        return None
    return observation.x, observation.y, observation.is_pinching
