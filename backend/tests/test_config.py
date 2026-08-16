import json

from backend.config import config_path, has_completed_setup, load_setup_config, save_setup_config


def test_missing_appdata_config_marks_the_application_as_first_run(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert config_path() == tmp_path / "windows-ai-files" / "config.json"
    assert has_completed_setup() is False
    assert load_setup_config() is None


def test_saved_folder_is_persisted_in_appdata_config_and_marks_setup_complete(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    selected_folder = r"C:\\Users\\Yusuf\\Documents\\Müvekkiller"

    save_setup_config(selected_folder)

    assert has_completed_setup() is True
    assert load_setup_config() == {"selectedFolder": selected_folder}
    assert json.loads(config_path().read_text(encoding="utf-8")) == {"selectedFolder": selected_folder}


def test_config_with_a_saved_folder_skips_first_run(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = tmp_path / "windows-ai-files" / "config.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"selectedFolder": r"D:\\Arşiv"}), encoding="utf-8")

    assert has_completed_setup() is True
    assert load_setup_config() == {"selectedFolder": r"D:\\Arşiv"}
