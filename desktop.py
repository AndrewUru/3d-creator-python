"""Windows desktop entrypoint: local Gradio server inside a native WebView2 window.

Run with --smoke-test to verify the bundled HTTP app without opening a window.
The server binds to loopback and is stopped when the desktop window closes.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
from urllib.request import urlopen


def configure_runtime() -> Path:
    """Keep writable data out of the read-only PyInstaller bundle."""
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    root = base / "Imagen-a-3D"
    root.mkdir(parents=True, exist_ok=True)
    cache = root / "gradio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    os.environ["GRADIO_TEMP_DIR"] = str(cache)
    os.environ["GRADIO_SHARE"] = "False"
    return root


def start_server():
    """Start the existing interface; do not change any generation callbacks."""
    import gradio as gr
    import uvicorn

    from app import CSS, create_app
    from imagen3d.storage import start_cleaner

    start_cleaner()
    demo = create_app().queue(max_size=16)
    # Import Uvicorn's lazy protocol modules before Gradio starts its thread.
    uvicorn.Config(app=demo.app, log_level="warning").load()
    demo.launch(
        server_name="127.0.0.1",
        server_port=None,  # Gradio finds a free local port.
        share=False,
        inbrowser=False,
        prevent_thread_lock=True,
        max_file_size="15mb",
        theme=gr.themes.Soft(primary_hue="cyan", neutral_hue="slate"),
        css=CSS,
        quiet=True,
    )
    return demo


def verify_server(url: str) -> None:
    """Basic executable health check for the Windows CI build."""
    with urlopen(url, timeout=20) as response:
        if response.status != 200 or not response.read(4096):
            raise RuntimeError("La interfaz no respondió correctamente.")


def show_failure(log_path: Path) -> None:
    message = (
        "No se pudo iniciar 3D Creator Studio.\n\n"
        f"Revisa el diagnóstico en:\n{log_path}\n\n"
        "Si no se abre la ventana, instala Microsoft Edge WebView2 Runtime."
    )
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "3D Creator Studio", 0x10)
    else:
        print(message, file=sys.stderr)


def main() -> int:
    runtime = configure_runtime()
    log_path = runtime / "desktop.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    smoke = "--smoke-test" in sys.argv
    demo = None
    try:
        demo = start_server()
        if smoke:
            verify_server(demo.local_url)
            logging.info("Windows portable smoke test OK: %s", demo.local_url)
            return 0

        # The UI must run on the main thread on Windows.
        import webview
        webview.create_window(
            "3D Creator Studio",
            demo.local_url,
            width=1400,
            height=900,
            min_size=(940, 660),
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    except Exception:
        logging.exception("No se pudo iniciar la aplicación")
        if not smoke:
            show_failure(log_path)
        return 1
    finally:
        if demo is not None:
            demo.close()


if __name__ == "__main__":
    raise SystemExit(main())
