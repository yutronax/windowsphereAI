import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.db_models import Base


def db_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set")
    return Path(appdata) / "windows-ai-files" / "app.db"


def _add_missing_columns(engine: Engine) -> None:
    """Saga #284: `Base.metadata.create_all` yeni TABLO eklemede
    idempotent ama VAR OLAN bir tabloya yeni bir KOLON eklendiğinde
    sessizce hiçbir şey yapmaz — gerçek kullanıcı makinelerinde `app.db`
    oluştuktan sonra bu, sessiz veri kaybına/`sqlite3.OperationalError:
    no such column` hatalarına yol açardı. Bu, alembic YERİNE bilinçli
    olarak seçilen minimal bir shim: eksik kolonları `ALTER TABLE ADD
    COLUMN` ile ekler. Kolon SİLME/tip DEĞİŞTİRME desteklemez (SQLite'ta
    bunlar tablo yeniden oluşturmayı gerektirir, bu MVP'de ihtiyaç yok)."""
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name not in inspector.get_table_names():
                continue  # yeni tablo, create_all zaten oluşturdu
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                column_type = column.type.compile(engine.dialect)
                if not column.nullable and column.default is None and column.server_default is None:
                    # Red-team bulgusu: bu shim SADECE `nullable=False`
                    # AÇIKÇA `NOT NULL` olarak eklenmezse çalışırdı — ama bu,
                    # taze kurulumlarda (create_all: NOT NULL doğru
                    # uygulanır) ile yükseltilmiş kurulumlarda (bu ALTER
                    # yolu: NOT NULL sessizce KAYBOLURDU) arasında sessiz bir
                    # şema sürüklenmesine yol açardı. Varsayılan değeri
                    # olmayan zorunlu bir kolon eklenmeye çalışılırsa, bu
                    # shim'in kapsamı dışında olduğu için AÇIKÇA/gürültülü
                    # biçimde başarısız oluyoruz (sessizce nullable'a
                    # düşürmek yerine).
                    raise RuntimeError(
                        f"Şema göçü desteklenmiyor: '{table.name}.{column.name}' "
                        "varsayılan değeri olmayan NOT NULL bir kolon olarak "
                        "eklenmeye çalışılıyor. Bu minimal shim (Saga #284) "
                        "sadece nullable veya varsayılan değerli yeni kolonları "
                        "destekler — gerçek bir migration aracı (alembic) "
                        "gerekiyor."
                    )
                connection.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}')
                )


def create_db_engine(db_url: str | None = None) -> Engine:
    if db_url is None:
        path = db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)
