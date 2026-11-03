from pathlib import Path
import shutil
import tempfile
import threading
import time
import uuid

ROOT = Path(tempfile.gettempdir()) / "imagen-a-3d"
TTL = 24 * 3600


def new_folder():
    ROOT.mkdir(exist_ok=True)
    folder = ROOT / uuid.uuid4().hex
    folder.mkdir()
    return folder


def cleanup():
    if ROOT.exists():
        for folder in ROOT.iterdir():
            if folder.is_dir() and not folder.is_symlink() and time.time() - folder.stat().st_mtime > TTL:
                shutil.rmtree(folder, ignore_errors=True)


def start_cleaner():
    cleanup()
    def loop():
        while True:
            time.sleep(600)
            cleanup()
    threading.Thread(target=loop, daemon=True).start()
