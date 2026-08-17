import os
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db_models import Base


def db_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set")
    return Path(appdata) / "windows-ai-files" / "app.db"


def create_db_engine(db_url: str | None = None) -> Engine:
    if db_url is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)
