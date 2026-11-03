from pathlib import Path
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from shapely import Polygon, make_valid, affinity, unary_union
import trimesh

MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 16_000_000


def read_image(path):
    if not path:
        raise ValueError("Sube una imagen PNG o JPG primero.")
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("El archivo supera 15 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as im:
                if im.format not in {"PNG", "JPEG"}:
                    raise ValueError("El contenido debe ser PNG o JPEG.")
                if im.width * im.height > MAX_PIXELS or max(im.size) > 8192 or min(im.size) < 8:
                    raise ValueError("Usa una imagen de al menos 8 × 8, hasta 8192 por lado y 16 megapíxeles.")
                im.load()
                return ImageOps.exif_transpose(im).convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("No se puede leer la imagen o su resolución es excesiva.") from exc


def mask_image(image, mode="Automática", threshold=127, invert=False, min_area=20, smooth=0):
    image = image.convert("RGBA")
    image.thumbnail((1600, 1600))
    rgba = np.asarray(image)
    alpha = rgba[:, :, 3]
    use_alpha = mode == "Transparencia" or (mode == "Automática" and alpha.min() < 255)
    if use_alpha:
        mask = (alpha > threshold).astype(np.uint8) * 255
    else:
        white = Image.new("RGBA", image.size, "white")
        gray = np.asarray(Image.alpha_composite(white, image).convert("L"))
        mask = (gray < threshold).astype(np.uint8) * 255
    if invert:
        mask = 255 - mask
    if smooth:
        k = int(smooth) * 2 + 1
        mask = (cv2.GaussianBlur(mask, (k, k), 0) >= 128).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = np.zeros(count, dtype=np.uint8)
    keep[1:] = (stats[1:, cv2.CC_STAT_AREA] >= min_area) * 255
    return keep[labels]


def polygon_parts(geometry):
    if geometry.geom_type == "Polygon":
        return [geometry] if geometry.area >= 1 else []
    return [p for g in getattr(geometry, "geoms", []) for p in polygon_parts(g)]


def contours_to_polygons(mask, simplify=0.8):
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise ValueError("La máscara está vacía. Cambia el umbral o la inversión.")
    tree = hierarchy[0]
    polygons = []
    repaired = 0
    for i, contour in enumerate(contours):
        depth, parent = 0, tree[i][3]
        while parent >= 0:
            depth += 1
            parent = tree[parent][3]
        if depth % 2 or len(contour) < 3:
            continue
        holes = [c[:, 0, :] for j, c in enumerate(contours) if tree[j][3] == i and len(c) >= 3]
        p = Polygon(contour[:, 0, :], holes)
        if not p.is_valid:
            repaired += 1
            p = make_valid(p)
        p = p.simplify(float(simplify), preserve_topology=True)
        polygons.extend(polygon_parts(p))
    if not polygons:
        raise ValueError("No hay contornos con área suficiente. Usa un dibujo más grande o reduce la limpieza.")
    if sum(len(p.exterior.coords) + sum(len(h.coords) for h in p.interiors) for p in polygons) > 50000:
        raise ValueError("Contorno demasiado complejo. Aumenta la simplificación o elimina pequeños restos.")
    return polygons, repaired


def build_mesh(mask, width=100, thickness=5, simplify=0.8, base=False, base_thickness=2):
    if not (1 <= width <= 1000 and 0.2 <= thickness <= 200 and 0.2 <= base_thickness <= 50):
        raise ValueError("Dimensiones fuera de rango.")
    polygons, repaired = contours_to_polygons(mask, simplify)
    bounds = unary_union(polygons).bounds
    scale = width / (bounds[2] - bounds[0])
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    shapes = [affinity.scale(affinity.translate(p, -center[0], -center[1]), xfact=scale, yfact=-scale, origin=(0, 0)) for p in polygons]
    meshes = [trimesh.creation.extrude_polygon(p, thickness, engine="earcut") for p in shapes]
    if base:
        # Overlap prevents a merely touching collection of shells.
        for mesh in meshes:
            mesh.apply_translation([0, 0, base_thickness - min(0.1, thickness / 2)])
        height = (bounds[3] - bounds[1]) * scale
        plate = trimesh.creation.box(extents=[width, height, base_thickness])
        plate.apply_translation([0, 0, base_thickness / 2])
        mesh = trimesh.boolean.union([plate, *meshes], engine="manifold")
    else:
        mesh = trimesh.util.concatenate(meshes)
    mesh.fix_normals(multibody=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume:
        raise ValueError("No se ha podido crear un sólido cerrado. Ajusta suavizado y simplificación.")
    return mesh, repaired


def export_mesh(mesh, folder):
    folder = Path(folder)
    stl, glb = folder / "modelo.stl", folder / "modelo.glb"
    mesh.export(stl)
    meters = mesh.copy()
    meters.apply_scale(0.001)
    meters.visual.vertex_colors = [55, 152, 190, 255]
    meters.export(glb)
    return str(stl), str(glb)


def report(mesh, repaired=0):
    dimensions = " × ".join(f"{v:.2f}" for v in mesh.extents)
    pieces = len(mesh.split(only_watertight=False))
    return (f"**Dimensiones:** {dimensions} mm · **Triángulos:** {len(mesh.faces):,}\n\n"
            f"**Piezas:** {pieces} · **Estanca:** {'sí' if mesh.is_watertight else 'no'} · "
            f"**Normales coherentes:** {'sí' if mesh.is_winding_consistent else 'no'} · Contornos reparados: {repaired}.\n\n"
            + ("Hay piezas desconectadas; activa la base para unirlas.\n\n" if pieces > 1 else "")
            + "Revisa el modelo en tu laminador: esta validación no garantiza que sea imprimible.")
