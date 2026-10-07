from array import array
import json
import math
from pathlib import Path
import time

import pygame

from src.config import (
    COW_SOUND_PATH,
    MUSIC_SETTINGS_PATH,
    SOUND_SETTINGS_PATH,
    TIGER_SOUND_PATH,
)


SAMPLE_RATE = 44100
AMPLITUDE = 9000
WIN_SOUND_DURATION_SECONDS = 120
LEGACY_PLAYER_SOUND_PATHS = {
    "tiger": TIGER_SOUND_PATH.resolve(),
    "cow": COW_SOUND_PATH.resolve(),
}


def _make_tone(frequencies: tuple[int, ...], duration: float) -> pygame.mixer.Sound:
    samples = array("h")
    samples_per_tone = int(SAMPLE_RATE * duration / len(frequencies))
    for frequency in frequencies:
        for sample_index in range(samples_per_tone):
            progress = sample_index / samples_per_tone
            envelope = min(progress * 12, (1 - progress) * 8, 1)
            sample = int(
                AMPLITUDE
                * envelope
                * math.sin(2 * math.pi * frequency * sample_index / SAMPLE_RATE)
            )
            samples.append(sample)
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _make_music() -> pygame.mixer.Sound:
    melody = (440, 523, 659, 523, 392, 494, 587, 494, 349, 440, 523, 440, 392, 494, 587, 494)
    bass = (110, 98, 87, 98)
    note_duration = 0.24
    samples_per_note = int(SAMPLE_RATE * note_duration)
    samples = array("h")
    for note_index, frequency in enumerate(melody):
        bass_frequency = bass[note_index // 4]
        for sample_index in range(samples_per_note):
            progress = sample_index / samples_per_note
            envelope = min(progress / 0.08, (1 - progress) / 0.18, 1)
            time = sample_index / SAMPLE_RATE
            value = (
                3600 * math.sin(2 * math.pi * frequency * time)
                + 1800 * math.sin(2 * math.pi * bass_frequency * time)
            )
            samples.append(int(value * max(0, envelope)))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _make_winner_music() -> pygame.mixer.Sound:
    melody = (523, 659, 784, 1047, 784, 880, 1047, 1319)
    bass = (131, 165, 196, 262)
    note_duration = 0.3
    samples_per_note = int(SAMPLE_RATE * note_duration)
    samples = array("h")
    for note_index, frequency in enumerate(melody):
        bass_frequency = bass[note_index // 2]
        for sample_index in range(samples_per_note):
            progress = sample_index / samples_per_note
            envelope = min(progress / 0.04, (1 - progress) / 0.12, 1)
            sample_time = sample_index / SAMPLE_RATE
            value = (
                4800 * math.sin(2 * math.pi * frequency * sample_time)
                + 2200 * math.sin(2 * math.pi * bass_frequency * sample_time)
            )
            samples.append(int(value * max(0, envelope)))
    return pygame.mixer.Sound(buffer=samples.tobytes())


class SoundEffects:
    def __init__(self) -> None:
        mixer_settings = (SAMPLE_RATE, -16, 1)
        if pygame.mixer.get_init() != mixer_settings:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
        pygame.mixer.set_reserved(2)
        self._music = _make_music()
        self._winner_music = _make_winner_music()
        self._music_channel = pygame.mixer.Channel(0)
        self._winner_channel = pygame.mixer.Channel(1)
        self._winner_deadline: float | None = None
        self._custom_music: pygame.mixer.Sound | None = None
        self._music_path: Path | None = None
        self._music_paused = False
        self._move = _make_tone((660,), 0.09)
        self._default_player_sound = _make_tone((880, 0, 880), 0.3)
        self._players = {
            "tiger": self._default_player_sound,
            "cow": self._default_player_sound,
        }
        self._draw = _make_tone((440, 392, 349), 0.72)
        self._player_paths = {
            "tiger": None,
            "cow": None,
        }
        self._volume = 0.7
        self._muted = False
        self._load_sound_settings()
        self._apply_volume()

    def start_music(self) -> None:
        saved_path = self._read_saved_music_path()
        if saved_path is not None and saved_path.is_file():
            try:
                self.set_music(saved_path, save=False)
                return
            except pygame.error as error:
                print(f"Could not load saved music {saved_path}: {error}")
        elif saved_path is not None:
            print(f"Saved music file is missing: {saved_path}")
        self._music_channel.play(self._music, loops=-1)
        if self._music_paused:
            self._music_channel.pause()

    def stop_music(self) -> None:
        self._music_channel.stop()
        pygame.mixer.music.stop()
        self.stop_winner()

    def stop_winner(self) -> None:
        self._winner_channel.stop()
        self._winner_deadline = None

    @property
    def music_path(self) -> Path | None:
        return self._music_path

    @property
    def music_paused(self) -> bool:
        return self._music_paused

    def toggle_music(self) -> None:
        if self._music_paused:
            self._music_channel.unpause()
            pygame.mixer.music.unpause()
        else:
            self._music_channel.pause()
            pygame.mixer.music.pause()
        self._music_paused = not self._music_paused

    def set_music(self, path: Path, *, save: bool = True) -> None:
        path = path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Music file not found: {path}")
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(0.22)
        pygame.mixer.music.play(loops=-1)
        if self._music_paused:
            pygame.mixer.music.pause()
        self._music_channel.stop()
        self._music_path = path
        self._apply_volume()
        if save:
            MUSIC_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            MUSIC_SETTINGS_PATH.write_text(str(path), encoding="utf-8")

    def _read_saved_music_path(self) -> Path | None:
        try:
            saved_path = MUSIC_SETTINGS_PATH.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        return Path(saved_path).expanduser() if saved_path else None

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def player_sound_paths(self) -> dict[str, Path | None]:
        return self._player_paths.copy()

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume()
        self._save_sound_settings()

    def toggle_mute(self) -> None:
        self._muted = not self._muted
        self._apply_volume()
        self._save_sound_settings()

    def set_player_sound(self, player: str, path: Path) -> None:
        if player not in self._players:
            raise ValueError(f"Unknown player sound: {player}")
        path = path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Sound file not found: {path}")
        sound = pygame.mixer.Sound(str(path))
        self._player_paths[player] = path
        self._players[player] = sound
        self._apply_volume()
        self._save_sound_settings()

    def reset_player_sounds(self) -> None:
        for player in self._players:
            self._players[player] = self._default_player_sound
            self._player_paths[player] = None
        self._apply_volume()
        self._save_sound_settings()

    def _apply_volume(self) -> None:
        volume = 0.0 if self._muted else self._volume
        self._music.set_volume(1.0)
        self._music_channel.set_volume(volume * 0.22)
        self._winner_channel.set_volume(volume * 0.65)
        self._move.set_volume(1.0)
        for sound in (*self._players.values(), self._winner_music, self._draw):
            sound.set_volume(1.0)
        for channel_index in range(2, pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(channel_index).set_volume(volume)
        if self._music_path is not None:
            pygame.mixer.music.set_volume(volume * 0.22)

    def _load_sound_settings(self) -> None:
        try:
            settings = json.loads(SOUND_SETTINGS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError) as error:
            print(f"Could not read sound settings: {error}")
            return
        if not isinstance(settings, dict):
            print("Could not read sound settings: expected a JSON object.")
            return

        volume = settings.get("volume", self._volume)
        muted = settings.get("muted", self._muted)
        if isinstance(volume, (int, float)) and not isinstance(volume, bool):
            self._volume = max(0.0, min(1.0, float(volume)))
        if isinstance(muted, bool):
            self._muted = muted

        player_paths = settings.get("player_sounds", {})
        if not isinstance(player_paths, dict):
            return
        for player, saved_path in player_paths.items():
            if player not in self._players or not isinstance(saved_path, str):
                continue
            path = Path(saved_path).expanduser()
            if path.resolve() == LEGACY_PLAYER_SOUND_PATHS[player]:
                continue
            if not path.is_file():
                print(f"Saved {player} sound file is missing: {path}")
                continue
            try:
                self._players[player] = pygame.mixer.Sound(str(path))
                self._player_paths[player] = path.resolve()
            except pygame.error as error:
                print(f"Could not load saved {player} sound {path}: {error}")

    def _save_sound_settings(self) -> None:
        settings = {
            "volume": self._volume,
            "muted": self._muted,
            "player_sounds": {
                player: str(path)
                for player, path in self._player_paths.items()
                if path is not None
            },
        }
        SOUND_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SOUND_SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def play_move(self) -> None:
        self._move.play()

    def play_player(self, player: str) -> None:
        self._players[player].play()

    def play_winner(self, winner: str) -> None:
        if winner not in {"tiger", "cow"}:
            raise ValueError(f"Unknown winner: {winner}")
        self._winner_channel.play(self._winner_music, loops=-1)
        self._winner_deadline = time.monotonic() + WIN_SOUND_DURATION_SECONDS

    def update(self) -> None:
        if (
            self._winner_deadline is not None
            and time.monotonic() >= self._winner_deadline
        ):
            self._winner_channel.stop()
            self._winner_deadline = None

    def play_draw(self) -> None:
        self._draw.play()
