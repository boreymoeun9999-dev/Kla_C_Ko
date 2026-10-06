import cv2
from cv2.typing import MatLike


class CameraError(RuntimeError):
    """Raised when a webcam cannot be opened."""


class Camera:
    def __init__(self, device_index: int) -> None:
        self.device_index = device_index
        self._capture: cv2.VideoCapture | None = None
        self._first_frame: MatLike | None = None
        for backend in _camera_backends():
            capture = cv2.VideoCapture(device_index, backend)
            if not capture.isOpened():
                capture.release()
                continue
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            success, frame = capture.read()
            if success:
                self._capture = capture
                self._first_frame = frame
                return
            capture.release()
        raise CameraError(
            f"Could not read camera {device_index}. Check camera permissions, "
            "close other camera apps, or connect another webcam."
        )

    def read(self) -> MatLike | None:
        if self._first_frame is not None:
            frame = self._first_frame
            self._first_frame = None
        else:
            if self._capture is None:
                return None
            success, frame = self._capture.read()
            if not success:
                return None
        return cv2.flip(frame, 1)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


def _camera_backends() -> tuple[int, ...]:
    backends = []
    for name in ("CAP_DSHOW", "CAP_MSMF", "CAP_ANY"):
        backend = getattr(cv2, name, None)
        if backend is not None and backend not in backends:
            backends.append(backend)
    return tuple(backends)


def open_player_cameras(
    player_names: tuple[str, ...],
    max_device_index: int = 5,
) -> tuple[dict[str, Camera | None], dict[str, str | None]]:
    cameras: dict[str, Camera | None] = {player: None for player in player_names}
    messages: dict[str, str | None] = {player: None for player in player_names}
    player_index = 0

    for device_index in range(max_device_index + 1):
        if player_index == len(player_names):
            break
        try:
            camera = Camera(device_index)
        except CameraError:
            continue
        cameras[player_names[player_index]] = camera
        player_index += 1

    available_players = [
        player for player in player_names if cameras[player] is not None
    ]
    if len(available_players) == 1 and len(player_names) > 1:
        shared_camera = cameras[available_players[0]]
        for player in player_names:
            cameras[player] = shared_camera
            messages[player] = None
    else:
        for player in player_names[player_index:]:
            messages[player] = (
                f"No webcam found for {player.title()}. Connect another camera "
                "and restart the game."
            )
    return cameras, messages
