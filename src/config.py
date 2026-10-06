from pathlib import Path

from src.game_rules import BOARD_SIZE


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = PROJECT_ROOT / "assets" / "png"
BACKGROUND_ASSET_DIR = PROJECT_ROOT / "assets" / "backgrounds"
SOUND_ASSET_DIR = PROJECT_ROOT / "assets" / "sounds"
TIGER_SOUND_PATH = SOUND_ASSET_DIR / "tiger-roar.mp3"
COW_SOUND_PATH = SOUND_ASSET_DIR / "cow-moo.mp3"
USER_SETTINGS_DIR = Path.home() / ".tiger_vs_cow"
MUSIC_SETTINGS_PATH = USER_SETTINGS_DIR / "music.txt"
SOUND_SETTINGS_PATH = USER_SETTINGS_DIR / "sound.json"
HAND_MODEL_PATH = PROJECT_ROOT / "assets" / "models" / "hand_landmarker.task"
WINDOW_WIDTH = 1360
WINDOW_HEIGHT = 760
FPS = 60
BOARD_TOP = 154
CELL_SIZE = 126
BOARD_PIXELS = CELL_SIZE * BOARD_SIZE
BOARD_LEFT = (WINDOW_WIDTH - BOARD_PIXELS) // 2
