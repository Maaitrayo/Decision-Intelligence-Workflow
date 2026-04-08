from pathlib import Path

from pipeline.config import get_settings
from pipeline.db import engine
from pipeline.db_models import Base


def init_db() -> None:
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./"):
        db_path = settings.database_url.removeprefix("sqlite:///./")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
