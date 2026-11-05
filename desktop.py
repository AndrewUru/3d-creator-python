"""Abre Imagen a 3D en una ventana propia, sin navegador."""
import socket

import webview

from app import start_server


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main(on_start=None):
    demo, url = start_server(free_port(), block=False)
    # Sin esto, los enlaces de descarga de STL y GLB no hacen nada en la ventana.
    webview.settings["ALLOW_DOWNLOADS"] = True
    window = webview.create_window("Imagen a 3D", url, width=1280, height=860, min_size=(900, 600))
    try:
        webview.start(on_start, window) if on_start else webview.start()
    finally:
        demo.close()


if __name__ == "__main__":
    main()
