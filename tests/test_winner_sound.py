import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.config import COW_SOUND_PATH, TIGER_SOUND_PATH
from src.sound_effects import (
    SAMPLE_RATE,
    WIN_SOUND_DURATION_SECONDS,
    SoundEffects,
)


class WinnerSoundTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=1)
        pygame.init()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_patch = patch(
            "src.sound_effects.SOUND_SETTINGS_PATH",
            Path(self.temp_dir.name) / "sound.json",
        )
        self.settings_patch.start()
        self.sounds = SoundEffects()

    def tearDown(self) -> None:
        self.sounds.stop_music()
        self.settings_patch.stop()
        pygame.quit()
        self.temp_dir.cleanup()

    def test_winner_music_loops_until_two_minute_deadline(self) -> None:
        with patch("src.sound_effects.time.monotonic", return_value=100.0):
            self.sounds.play_winner("tiger")

        self.assertEqual(WIN_SOUND_DURATION_SECONDS, 120)
        self.assertTrue(pygame.mixer.Channel(1).get_busy())

        with patch("src.sound_effects.time.monotonic", return_value=219.9):
            self.sounds.update()
        self.assertTrue(pygame.mixer.Channel(1).get_busy())

        with patch("src.sound_effects.time.monotonic", return_value=220.0):
            self.sounds.update()
        self.assertFalse(pygame.mixer.Channel(1).get_busy())

    def test_both_winners_use_the_same_celebration_music(self) -> None:
        channel = Mock()
        self.sounds._winner_channel = channel
        with patch("src.sound_effects.time.monotonic", return_value=10.0):
            self.sounds.play_winner("cow")
            self.sounds.play_winner("tiger")
        self.assertEqual(channel.play.call_count, 2)
        self.assertIs(
            channel.play.call_args_list[0].args[0],
            channel.play.call_args_list[1].args[0],
        )
        self.assertEqual(channel.play.call_args.kwargs, {"loops": -1})
        self.assertNotEqual(
            self.sounds._winner_music.get_raw(),
            self.sounds._players["tiger"].get_raw(),
        )

    def test_both_players_use_short_beep_sounds_by_default(self) -> None:
        self.assertEqual(
            self.sounds.player_sound_paths,
            {"tiger": None, "cow": None},
        )
        self.assertLess(self.sounds._players["tiger"].get_length(), 0.5)
        self.assertIs(
            self.sounds._players["tiger"],
            self.sounds._players["cow"],
        )
        self.assertEqual(
            self.sounds._players["tiger"].get_raw(),
            self.sounds._players["cow"].get_raw(),
        )
        self.assertNotEqual(
            self.sounds._winner_music.get_raw(),
            self.sounds._players["tiger"].get_raw(),
        )

    def test_legacy_packaged_animal_sounds_migrate_to_beep_defaults(self) -> None:
        settings_path = Path(self.temp_dir.name) / "sound.json"
        settings_path.write_text(
            json.dumps(
                {
                    "player_sounds": {
                        "tiger": str(TIGER_SOUND_PATH),
                        "cow": str(COW_SOUND_PATH),
                    }
                }
            ),
            encoding="utf-8",
        )

        restored_sounds = SoundEffects()

        self.assertEqual(
            restored_sounds.player_sound_paths,
            {"tiger": None, "cow": None},
        )
        self.assertEqual(
            restored_sounds._players["tiger"].get_raw(),
            restored_sounds._players["cow"].get_raw(),
        )

    def test_closing_winner_panel_stops_celebration_music(self) -> None:
        with patch("src.sound_effects.time.monotonic", return_value=10.0):
            self.sounds.play_winner("tiger")
        self.assertTrue(pygame.mixer.Channel(1).get_busy())

        self.sounds.stop_winner()

        self.assertFalse(pygame.mixer.Channel(1).get_busy())
        self.assertIsNone(self.sounds._winner_deadline)


if __name__ == "__main__":
    unittest.main()
