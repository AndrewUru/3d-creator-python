"""Desktop entrypoint: local Gradio server displayed in a native window."""
import os
import sys
import traceback
import webbrowser

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

from app import CSS, create_app
from imagen3d.storage import start_cleaner


def main():
    import gradio as gr
    import uvicorn

    start_cleaner()
    demo = create_app().queue(max_size=16)
    uvicorn.Config(app=demo.app, log_level="warning").load()
    try:
        demo.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            inbrowser=False,
            prevent_thread_lock=True,
            max_file_size="15mb",
            theme=gr.themes.Soft(primary_hue="cyan", neutral_hue="slate"),
            css=CSS,
        )
        url = demo.local_url or "http://127.0.0.1:7860"
        try:
            import webview
            webview.create_window("3D Creator Studio", url, width=1360, height=900,
                                  min_size=(850, 600))
            webview.start()
        except Exception as exc:
            print(f"No se pudo abrir la ventana nativa: {exc}", file=sys.stderr)
            print(f"Abriendo la interfaz en el navegador: {url}")
            webbrowser.open(url)
            input("Pulsa Intro para detener el servidor... ")
    finally:
        demo.close()


if __name__ == "__main__":
    try:
        if "--check" in sys.argv:
            import trimesh
            instance = create_app()
            assert instance is not None
            print("OK: dependencias e interfaz cargadas.")
        else:
            main()
    except Exception:
        traceback.print_exc()
        input("Error al arrancar. Pulsa Intro para salir... ")
        sys.exit(1)
