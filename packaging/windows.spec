# -*- mode: python ; coding: utf-8 -*-
"""Windows x64 onedir build. Run: python -m PyInstaller packaging/windows.spec"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent
datas = []
binaries = []
hiddenimports = []

# Gradio serves a packaged JS/CSS frontend; it is not enough to import
# the Python modules without their static data and package metadata.
for package in ("gradio", "gradio_client", "webview"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas.extend(package_data)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_imports)

# Uvicorn chooses its transport/protocol implementations dynamically.
hiddenimports.extend(collect_submodules("uvicorn"))

a = Analysis(
    [str(ROOT / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torchvision", "transformers", "tensorflow"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="3D-Creator",
    console=False,
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="3D-Creator",
)
