import pytest


@pytest.fixture(autouse=True)
def _reset_db_session_factory_cache():
    """Saga #318 red-team bulgusu: `backend.main._db_session_factory`
    süreç başına bir kez oluşturulup modül seviyesinde önbelleğe alınıyor
    (bkz. `_get_db_session_factory` docstring'i). `get_db_session`'ı
    `app.dependency_overrides` ile override etmeyen testler bu cache'i
    kullanıyor — cache testler arasında sıfırlanmazsa, ilk testin
    `APPDATA`'sıyla kurulan engine sonraki testlerin farklı
    `monkeypatch.setenv("APPDATA", ...)` değerlerini görmeden eski (ve
    artık silinmiş olabilecek) bir tmp_path veritabanına bağlı kalır.
    Bu fixture her testten önce cache'i `None`'a resetler."""
    import backend.main as main_module

    main_module._db_session_factory = None
    yield
    main_module._db_session_factory = None
