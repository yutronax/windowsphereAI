import json
import os
from pathlib import Path


def config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set")
    return Path(appdata) / "windows-ai-files" / "config.json"


def load_setup_config() -> dict[str, str] | None:
    path = config_path()
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(config.get("selectedFolder"), str):
        return None
    return {"selectedFolder": config["selectedFolder"]}


def has_completed_setup() -> bool:
    return load_setup_config() is not None


def save_setup_config(folder: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"selectedFolder": folder}), encoding="utf-8")
