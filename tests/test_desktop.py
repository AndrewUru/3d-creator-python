from pathlib import Path

from desktop import configure_runtime


def test_runtime_directories_are_writable_outside_bundle(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("GRADIO_TEMP_DIR", raising=False)
    monkeypatch.setenv("GRADIO_ANALYTICS_ENABLED", "True")
    root = configure_runtime()
    assert root == tmp_path / "Imagen-a-3D"
    assert root.is_dir()
    assert Path(__import__("os").environ["GRADIO_TEMP_DIR"]).is_dir()
    assert __import__("os").environ["GRADIO_ANALYTICS_ENABLED"] == "False"
    assert __import__("os").environ["GRADIO_SHARE"] == "False"
