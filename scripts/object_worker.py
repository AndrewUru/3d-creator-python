"""Offline TripoSR reconstruction. Runs in its own CPU environment."""
from pathlib import Path
import os
import sys
import json
import numpy as np
import torch
from PIL import Image
import rembg

ROOT = Path(__file__).resolve().parents[1]
os.environ['U2NET_HOME'] = str(ROOT / 'models' / 'rembg')
os.environ['IMAGEN3D_DINO_CONFIG'] = str(ROOT / 'models' / 'TripoSR' / 'dino-config.json')
sys.path.insert(0, str(ROOT / 'runtime' / 'TripoSR'))
from tsr.system import TSR
from tsr.utils import resize_foreground


def main():
    source, folder = Path(sys.argv[1]), Path(sys.argv[2])
    size, resolution = float(sys.argv[3]), int(sys.argv[4])
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    print('Separando el objeto del fondo...', flush=True)
    image = Image.open(source).convert('RGBA')
    image.thumbnail((1024, 1024))
    if image.getchannel('A').getextrema()[0] == 255:
        session = rembg.new_session('u2netp', providers=['CPUExecutionProvider'])
        image = rembg.remove(image, session=session)
        del session
    alpha = np.asarray(image)[:, :, 3]
    if np.count_nonzero(alpha > 127) < 64:
        raise ValueError('No se pudo separar el objeto; utiliza un PNG con fondo transparente.')
    image.save(folder / 'objeto-recortado.png')
    image = resize_foreground(image, 0.85)
    rgba = np.asarray(image).astype(np.float32) / 255
    prepared = Image.fromarray(np.uint8(np.clip(rgba[:, :, :3] * rgba[:, :, 3:4] + 0.5 * (1-rgba[:, :, 3:4]), 0, 1) * 255))
    prepared.save(folder / 'entrada-modelo.png')
    print('Cargando el modelo 3D local...', flush=True)
    model = TSR.from_pretrained(str(ROOT / 'models' / 'TripoSR'), 'config.yaml', 'model.ckpt').eval()
    model.renderer.set_chunk_size(4096)
    print('Reconstruyendo el objeto completo en CPU...', flush=True)
    with torch.inference_mode():
        codes = model([prepared], device='cpu')
        print('Extrayendo la superficie y sus colores...', flush=True)
        mesh = model.extract_mesh(codes, has_vertex_color=True, resolution=resolution)[0]
    if len(mesh.faces) < 4 or not np.isfinite(mesh.vertices).all() or mesh.extents.max() <= 0:
        raise ValueError('El modelo no produjo una superficie válida.')
    mesh.fix_normals(multibody=True)
    mesh.apply_scale(size / mesh.extents.max())
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
    mesh.export(folder / 'objeto.stl')
    meters = mesh.copy()
    meters.apply_scale(0.001)
    meters.export(folder / 'objeto.glb')
    (folder / 'resultado.json').write_text(json.dumps({'dimensions': mesh.extents.tolist(), 'faces': len(mesh.faces),
        'watertight': bool(mesh.is_watertight), 'parts': len(mesh.split(only_watertight=False))}), encoding='utf-8')
    print('Objeto completo exportado.', flush=True)


if __name__ == '__main__':
    main()
