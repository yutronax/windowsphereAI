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


def load_history_cleared_at() -> str | None:
    path = config_path()
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    cleared_at = config.get("historyClearedAt")
    if isinstance(cleared_at, str):
        return cleared_at
    return None


def load_history_cleared_before_id() -> int | None:
    # "Geçmişi Temizle" filtresinin GERÇEK kaynağı bu — `historyClearedAt`
    # (ISO timestamp) sadece API yanıtı/gösterim amaçlıdır. Transaction id'leri
    # DB'de monotonik/atomik arttığı için (flush anında atanır), saat
    # çözünürlüğü/tie sorunlarından TAMAMEN bağımsız, güvenilir bir sınır
    # sağlar — canlı testte `created_at` bazlı bir eşiğin (hatta cömert bir
    # epsilon ile bile) art arda hızlı DB işlemlerinde flaky olduğu kanıtlandı.
    path = config_path()
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as file:
            config = json.load(file)
    except (json.JSONDecodeError, OSError):
        return None

    cleared_before_id = config.get("historyClearedBeforeId")
    if isinstance(cleared_before_id, int):
        return cleared_before_id
    return None


def has_completed_setup() -> bool:
    return load_setup_config() is not None


def save_setup_config(
    folder: str | None = None,
    history_cleared_at: str | None = None,
    history_cleared_before_id: int | None = None,
) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Mevcut config'i oku ve güncelle (sadece verilen alanları değiştir)
    config: dict[str, str | int] = {}
    if path.exists():
        try:
            with path.open(encoding="utf-8") as file:
                existing = json.load(file)
                if isinstance(existing, dict):
                    config = existing
        except (json.JSONDecodeError, OSError):
            pass

    # Verilen alanları güncelle
    if folder is not None:
        config["selectedFolder"] = folder
    if history_cleared_at is not None:
        config["historyClearedAt"] = history_cleared_at
    if history_cleared_before_id is not None:
        config["historyClearedBeforeId"] = history_cleared_before_id

    path.write_text(json.dumps(config), encoding="utf-8")
