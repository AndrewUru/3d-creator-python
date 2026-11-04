"""Local height fields and closed, dimensioned relief meshes."""
from pathlib import Path
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image
import trimesh

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "depth-anything-v2-small"
PYTHON = ROOT / ".venv-ai" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def depth_available():
    return PYTHON.exists() and (MODEL / "ready.ok").exists()


def estimate_depth(image, folder):
    if not depth_available():
        if getattr(sys, "frozen", False):
            raise ValueError("La versión portable aún no incluye Depth Anything. Utiliza la instalación Python para el modo fotografía IA.")
        raise ValueError("Instala el modelo gratuito: .venv/Scripts/python scripts/install_depth.py")
    source, target = Path(folder) / "entrada.png", Path(folder) / "profundidad.npy"
    # Bound inference output and strip metadata before the local worker.
    image = image.copy()
    image.thumbnail((1024, 1024))
    background = Image.new("RGBA", image.size, "white")
    Image.alpha_composite(background, image.convert("RGBA")).convert("RGB").save(source)
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    try:
        subprocess.run([str(PYTHON), str(ROOT / "scripts" / "depth_worker.py"), str(source), str(target)],
                       check=True, capture_output=True, timeout=600, env=env)
    except subprocess.TimeoutExpired:
        raise ValueError("La estimación local superó 10 minutos. Prueba una imagen más pequeña.") from None
    except (subprocess.CalledProcessError, OSError):
        raise ValueError("Falló el modelo local. Reinstálalo con scripts/install_depth.py.") from None
    return np.load(target, allow_pickle=False)


def prepare_heights(image, depth=None, resolution=192, smooth=1, invert=False, gamma=1):
    if not 32 <= resolution <= 384 or not 0 <= smooth <= 5 or not 0.25 <= gamma <= 4:
        raise ValueError("Ajustes de relieve fuera de rango.")
    rgba = np.asarray(image.convert("RGBA"))
    if not np.any(rgba[:, :, 3]):
        raise ValueError("La imagen es completamente transparente.")
    height = max(2, round(resolution * image.height / max(image.size)))
    width = max(2, round(resolution * image.width / max(image.size)))
    if depth is None:
        values = np.asarray(image.convert("L"), dtype=float) / 255
    else:
        values = np.asarray(depth, dtype=float)
        if values.ndim != 2 or not np.isfinite(values).all():
            raise ValueError("Mapa de profundidad no válido.")
        low, high = np.percentile(values, [1, 99])
        values = np.clip((values - low) / max(high - low, 1e-8), 0, 1)
    values = cv2.resize(values, (width, height), interpolation=cv2.INTER_AREA)
    if smooth:
        values = cv2.GaussianBlur(values, (0, 0), float(smooth))
    if invert:
        values = 1 - values
    alpha = cv2.resize(rgba[:, :, 3].astype(float) / 255, (width, height), interpolation=cv2.INTER_AREA)
    return np.clip(values, 0, 1) ** gamma * alpha


def build_relief(heights, width=100, relief=5, base=2, aspect=1):
    heights = np.asarray(heights, dtype=float)
    if heights.ndim != 2 or min(heights.shape) < 2 or max(heights.shape) > 384:
        raise ValueError("El mapa debe tener entre 2 y 384 puntos por lado.")
    if not np.isfinite(heights).all() or heights.min() < 0 or heights.max() > 1:
        raise ValueError("Las alturas deben estar entre 0 y 1.")
    if not (1 <= width <= 1000 and 0.2 <= relief <= 100 and 0.2 <= base <= 50 and 0 < aspect <= 1024):
        raise ValueError("Dimensiones fuera de rango.")
    rows, cols = heights.shape
    x, y = np.meshgrid(np.linspace(-width/2, width/2, cols), np.linspace(width*aspect/2, -width*aspect/2, rows))
    top = np.column_stack([x.ravel(), y.ravel(), base + relief * heights.ravel()])
    bottom = top.copy()
    bottom[:, 2] = 0
    n = len(top)
    a = (np.arange(rows-1)[:, None]*cols + np.arange(cols-1)).ravel()
    faces = np.vstack([np.column_stack([a, a+cols, a+1]), np.column_stack([a+1, a+cols, a+cols+1])])
    bottom_faces = faces[:, ::-1] + n
    ring = np.concatenate([np.arange(cols), np.arange(1, rows)*cols+cols-1,
                           (rows-1)*cols+np.arange(cols-2, -1, -1), np.arange(rows-2, 0, -1)*cols])
    nxt = np.roll(ring, -1)
    sides = np.vstack([np.column_stack([ring, nxt, ring+n]), np.column_stack([nxt, nxt+n, ring+n])])
    mesh = trimesh.Trimesh(vertices=np.vstack([top, bottom]), faces=np.vstack([faces, bottom_faces, sides]), process=True)
    mesh.fix_normals(multibody=False)
    if not mesh.is_volume or not mesh.is_watertight or not mesh.is_winding_consistent:
        raise ValueError("No se pudo cerrar el relieve.")
    return mesh
