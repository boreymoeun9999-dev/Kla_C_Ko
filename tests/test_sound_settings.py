import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.sound_effects import SAMPLE_RATE, SoundEffects


class SoundSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=1)
        pygame.init()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.music_file = self.directory / "custom-song.wav"
        with wave.open(str(self.music_file), "wb") as music_file:
            music_file.setnchannels(1)
            music_file.setsampwidth(2)
            music_file.setframerate(SAMPLE_RATE)
            music_file.writeframes(b"\0\0" * SAMPLE_RATE)
        self.settings_file = self.directory / "music.txt"
        self.settings_patch = patch(
            "src.sound_effects.MUSIC_SETTINGS_PATH",
            self.settings_file,
        )
        self.settings_patch.start()
        self.sound_settings_file = self.directory / "sound.json"
        self.sound_settings_patch = patch(
            "src.sound_effects.SOUND_SETTINGS_PATH",
            self.sound_settings_file,
        )
        self.sound_settings_patch.start()

    def tearDown(self) -> None:
        self.settings_patch.stop()
        self.sound_settings_patch.stop()
        pygame.mixer.music.stop()
        pygame.quit()
        self.temp_dir.cleanup()

    def test_selected_music_is_saved_and_restored_on_startup(self) -> None:
        sounds = SoundEffects()
        sounds.set_music(self.music_file)
        saved_path = self.music_file.resolve()

        self.assertEqual(self.settings_file.read_text(encoding="utf-8"), str(saved_path))
        self.assertEqual(sounds.music_path, saved_path)

        restored_sounds = SoundEffects()
        restored_sounds.start_music()
        self.assertEqual(restored_sounds.music_path, saved_path)
        self.assertTrue(pygame.mixer.music.get_busy())
        restored_sounds.stop_music()

    def test_missing_music_file_is_reported(self) -> None:
        sounds = SoundEffects()
        missing_file = self.directory / "missing.wav"

        with self.assertRaises(FileNotFoundError):
            sounds.set_music(missing_file)

    def test_music_toggle_pauses_and_resumes_selected_song(self) -> None:
        sounds = SoundEffects()
        sounds.set_music(self.music_file)

        sounds.toggle_music()
        self.assertTrue(sounds.music_paused)
        self.assertFalse(pygame.mixer.music.get_busy())

        sounds.toggle_music()
        self.assertFalse(sounds.music_paused)
        self.assertTrue(pygame.mixer.music.get_busy())

    def test_volume_mute_and_custom_player_sounds_are_saved(self) -> None:
        sounds = SoundEffects()
        sounds.set_player_sound("tiger", self.music_file)
        sounds.set_volume(0.4)
        sounds.play_player("cow")
        self.assertTrue(pygame.mixer.Channel(2).get_busy())
        sounds.toggle_mute()
        self.assertEqual(pygame.mixer.Channel(2).get_volume(), 0.0)

        restored_sounds = SoundEffects()
        self.assertEqual(restored_sounds.volume, 0.4)
        self.assertTrue(restored_sounds.muted)
        self.assertEqual(
            restored_sounds.player_sound_paths["tiger"],
            self.music_file.resolve(),
        )
        restored_sounds.toggle_mute()
        self.assertFalse(restored_sounds.muted)
        self.assertAlmostEqual(pygame.mixer.Channel(0).get_volume(), 0.22 * 0.4, places=2)


if __name__ == "__main__":
    unittest.main()
