from __future__ import annotations

from pathlib import Path
import time
from collections.abc import Callable
from typing import Protocol

import pygame
from cv2.typing import MatLike
from tkinter import Tk, filedialog

from src.camera import Camera, open_player_cameras
from src.config import FPS, WINDOW_HEIGHT, WINDOW_WIDTH
from src.ai_player import AI_DIFFICULTIES, play_ai_turn
from src.game_state import GameState, TOTAL_COWS
from src.game_rules import legal_cow_moves, legal_tiger_moves
from src.gesture_recognizer import (
    BoardThemeGestureRecognizer,
    GestureRecognizer,
    HandInput,
    map_to_board,
)
from src.hand_tracker import HandObservation, HandTracker
from src.renderer import Renderer
from src.sound_effects import SAMPLE_RATE, SoundEffects


PLAYERS = ("tiger", "cow")
PLAYER_HANDS = {"tiger": "right", "cow": "left"}
AI_MOVE_DELAY_SECONDS = 0.45


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
    theme_gestures = {
        player: BoardThemeGestureRecognizer() for player in PLAYERS
    }
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
    ai_turn_deadline: float | None = None
    try:
        if sounds.music_path is not None:
            renderer.music_label = sounds.music_path.name
        renderer.sound_volume = sounds.volume
        renderer.sound_muted = sounds.muted
        renderer.music_paused = sounds.music_paused
        renderer.player_sound_labels.update(
            {
                player: path.name if path is not None else "Beep beep"
                for player, path in sounds.player_sound_paths.items()
            }
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
                            _configure_ai_opponent(renderer)
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
                        if _handle_start_screen_click(event.pos, renderer):
                            game_started = True
                            _configure_ai_opponent(renderer)
                            sounds.start_music()

                if not game_started:
                    camera_started, camera_cursor = _camera_clicked_start(
                        cameras,
                        trackers,
                        gestures,
                        renderer.start_button_rect,
                        click_handler=lambda position: _handle_start_screen_click(
                            position, renderer
                        ),
                    )
                    if camera_started:
                        if renderer.active_name_field is not None:
                            pygame.key.stop_text_input()
                        game_started = True
                        _configure_ai_opponent(renderer)
                        sounds.start_music()

                renderer.draw_start_screen(camera_cursor)
                pygame.display.flip()
                clock.tick(FPS)
                continue

            cursor = None
            gestures_this_frame = {}
            gesture_positions = {}
            camera_clicks: list[
                tuple[str, tuple[int, int], tuple[int, int]]
            ] = []
            active_player = (
                state.current_turn
                if state.current_turn != renderer.ai_player
                else None
            )
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
                observation = hands_by_camera[device_index]
                theme_gesture = (
                    observation.theme_gesture
                    if player != renderer.ai_player
                    and observation is not None
                    and observation.handedness.casefold() == PLAYER_HANDS[player]
                    else None
                )
                selected_theme = theme_gestures[player].update(theme_gesture)
                if selected_theme is not None:
                    renderer.board_theme_index = selected_theme
                normalized_cursor, gesture_click = gestures[player].update(hand)
                gestures_this_frame[player] = gesture_click
                if normalized_cursor is not None:
                    gesture_positions[player] = normalized_cursor
                    if gesture_click:
                        screen_position = map_to_board(
                            normalized_cursor,
                            0,
                            0,
                            WINDOW_WIDTH,
                            WINDOW_HEIGHT,
                        )
                        board_position = map_to_board(
                            normalized_cursor,
                            renderer.board_rect.left,
                            renderer.board_rect.top,
                            renderer.board_rect.width,
                            renderer.board_rect.height,
                        )
                        camera_clicks.append(
                            (player, screen_position, board_position)
                        )

            if active_player is not None:
                hand_position = gesture_positions.get(active_player)
                if hand_position is not None:
                    screen_cursor = map_to_board(
                        hand_position,
                        0,
                        0,
                        WINDOW_WIDTH,
                        WINDOW_HEIGHT,
                    )
                    cursor = (
                        screen_cursor
                        if _is_game_control_position(renderer, screen_cursor)
                        else map_to_board(
                            hand_position,
                            renderer.board_rect.left,
                            renderer.board_rect.top,
                            renderer.board_rect.width,
                            renderer.board_rect.height,
                        )
                    )
            if cursor is None and gesture_positions:
                hand_position = next(iter(gesture_positions.values()))
                cursor = map_to_board(
                    hand_position,
                    0,
                    0,
                    WINDOW_WIDTH,
                    WINDOW_HEIGHT,
                )

            for camera_player, screen_position, board_position in camera_clicks:
                if _is_game_control_position(renderer, screen_position):
                    action = _handle_game_click(
                        screen_position,
                        state,
                        renderer,
                        sounds,
                    )
                    if action == "quit":
                        running = False
                    elif action == "home":
                        ai_turn_deadline = None
                        game_started = False
                        renderer.focus_name_field(
                            renderer.name_field_rects["tiger"].center
                        )
                        pygame.key.start_text_input()
                elif (
                    not renderer.sound_settings_open
                    and camera_player != renderer.ai_player
                    and camera_player == state.current_turn
                ):
                    _handle_click(
                        camera_player,
                        board_position,
                        state,
                        renderer,
                        sounds,
                    )

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
                        ai_turn_deadline = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = _handle_game_click(
                        event.pos,
                        state,
                        renderer,
                        sounds,
                    )
                    if action == "quit":
                        running = False
                    elif action == "home":
                        sounds.stop_winner()
                        ai_turn_deadline = None
                        game_started = False
                        renderer.focus_name_field(
                            renderer.name_field_rects["tiger"].center
                        )
                        pygame.key.start_text_input()

            if (
                renderer.ai_player is not None
                and state.current_turn == renderer.ai_player
                and not state.is_over
                and not renderer.sound_settings_open
            ):
                if ai_turn_deadline is None:
                    ai_turn_deadline = time.monotonic() + AI_MOVE_DELAY_SECONDS
                elif time.monotonic() >= ai_turn_deadline:
                    ai_player = state.current_turn
                    if (
                        play_ai_turn(
                            state,
                            depth=AI_DIFFICULTIES[renderer.ai_strength],
                        )
                        and ai_player is not None
                    ):
                        if state.winner is not None:
                            _play_action_sound(state, sounds)
                        else:
                            sounds.play_player(ai_player)
                    ai_turn_deadline = None
            else:
                ai_turn_deadline = None

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
    click_handler: Callable[[tuple[int, int]], bool] | None = None,
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
        if gesture_click:
            if click_handler is not None:
                if click_handler(cursor):
                    return True, cursor
            elif start_button_rect.collidepoint(cursor):
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
    elif renderer.settings_reset_sounds_rect.collidepoint(position):
        sounds.reset_player_sounds()
        renderer.player_sound_labels.update(
            {"tiger": "Beep beep", "cow": "Beep beep"}
        )
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


def _configure_ai_opponent(renderer: Renderer) -> None:
    renderer.ai_player = (
        "cow" if renderer.human_player == "tiger" else "tiger"
    ) if renderer.play_mode == "ai" else None


def _handle_start_screen_click(
    position: tuple[int, int],
    renderer: Renderer,
) -> bool:
    if renderer.focus_name_field(position):
        pygame.key.start_text_input()
        return False

    pygame.key.stop_text_input()
    if renderer.play_two_player_rect.collidepoint(position):
        renderer.play_mode = "two-player"
    elif renderer.play_ai_rect.collidepoint(position):
        renderer.play_mode = "ai"
    elif renderer.play_as_tiger_rect.collidepoint(position):
        renderer.human_player = "tiger"
    elif renderer.play_as_cow_rect.collidepoint(position):
        renderer.human_player = "cow"
    elif renderer.play_mode == "ai":
        for strength, rect in renderer.ai_strength_rects.items():
            if rect.collidepoint(position):
                renderer.ai_strength = strength
                break
    return renderer.start_button_rect.collidepoint(position)


def _is_game_control_position(
    renderer: Renderer,
    position: tuple[int, int],
) -> bool:
    controls = (
        renderer.home_rect,
        renderer.forfeit_rect,
        renderer.sound_settings_rect,
        renderer.music_toggle_rect,
        renderer.close_rect,
        renderer.restart_rect,
        renderer.music_rect,
    )
    modal_controls = (
        renderer.settings_tiger_rect,
        renderer.settings_cow_rect,
        renderer.settings_volume_down_rect,
        renderer.settings_volume_up_rect,
        renderer.settings_mute_rect,
        renderer.settings_reset_sounds_rect,
        renderer.settings_close_rect,
    )
    return any(rect.collidepoint(position) for rect in controls) or (
        renderer.sound_settings_open
        and any(rect.collidepoint(position) for rect in modal_controls)
    )


def _handle_game_click(
    position: tuple[int, int],
    state: GameState,
    renderer: Renderer,
    sounds: SoundEffects,
) -> str | None:
    if renderer.sound_settings_open:
        _handle_sound_settings_click(position, renderer, sounds)
    elif renderer.home_rect.collidepoint(position):
        sounds.stop_winner()
        state.reset()
        renderer.ai_player = None
        return "home"
    elif renderer.forfeit_rect.collidepoint(position):
        player = state.current_turn
        if (
            player is not None
            and player != renderer.ai_player
            and state.forfeit(player)
        ):
            _play_action_sound(state, sounds)
    elif renderer.sound_settings_rect.collidepoint(position):
        renderer.sound_settings_open = True
    elif renderer.music_toggle_rect.collidepoint(position):
        sounds.toggle_music()
        renderer.music_paused = sounds.music_paused
    elif renderer.close_rect.collidepoint(position):
        return "quit"
    elif renderer.restart_rect.collidepoint(position):
        sounds.stop_winner()
        state.reset()
    elif renderer.music_rect.collidepoint(position):
        music_path = _choose_music_file()
        if music_path is not None:
            try:
                sounds.set_music(music_path)
                renderer.music_label = music_path.name
            except (pygame.error, OSError) as error:
                renderer.music_label = "Song error"
                print(f"Could not load selected music: {error}")
    elif state.current_turn != renderer.ai_player:
        _handle_click(state.current_turn, position, state, renderer, sounds)
    return None


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
