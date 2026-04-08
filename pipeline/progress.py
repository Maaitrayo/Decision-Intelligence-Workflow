from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass
class ProgressState:
    stage: str = "idle"
    message: str = "Idle"
    running: bool = False
    updated_at: str = ""


class ProgressTracker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state = ProgressState(updated_at=self._now())

    def get_state(self) -> dict[str, str | bool]:
        with self._lock:
            return asdict(self._state)

    def set_state(self, stage: str, message: str, running: bool) -> None:
        with self._lock:
            self._state = ProgressState(
                stage=stage,
                message=message,
                running=running,
                updated_at=self._now(),
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


progress_tracker = ProgressTracker()
