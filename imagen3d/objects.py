"""Offline object reconstruction, separate from height-map reliefs."""
from pathlib import Path
import os
import subprocess
import json
import time
import sys
from .geometry import read_image
from .storage import new_folder

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv-tripo' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def generate_object(path, size, resolution):
    try:
        if not (1 <= size <= 1000 and resolution in (96, 128, 192)):
            raise ValueError('Tamaño entre 1 y 1000 mm y resolución 96, 128 o 192.')
        image = read_image(path)
        if not PYTHON.exists() or not (ROOT / 'models/TripoSR/installed.ok').exists():
            if getattr(sys, 'frozen', False):
                raise ValueError('La versión portable aún no incluye el motor TripoSR. Utiliza la instalación Python para reconstruir objetos completos.')
            raise ValueError('Instala la IA gratuita con: .venv/Scripts/python scripts/install_local_ai.py')
        folder = new_folder()
        image.thumbnail((1024, 1024))
        source = folder / 'original.png'
        image.save(source)
        env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', PYTHONIOENCODING='utf-8')
        yield None, None, None, None, 'Preparando reconstrucción local. En CPU puede tardar varios minutos.'
        with (folder / 'proceso.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([str(PYTHON), str(ROOT / 'scripts/object_worker.py'), str(source), str(folder), str(size), str(int(resolution))],
                                       stdout=log, stderr=log, env=env)
            started = time.monotonic()
            last_stage = ''
            try:
                while process.poll() is None:
                    if time.monotonic() - started > 1800:
                        raise ValueError('La reconstrucción superó 30 minutos; prueba resolución 96.')
                    time.sleep(2)
                    lines = (folder / 'proceso.log').read_text(encoding='utf-8', errors='replace').splitlines()
                    stages = [line for line in lines if line.startswith(('Separando', 'Cargando', 'Reconstruyendo', 'Extrayendo'))]
                    if stages and stages[-1] != last_stage:
                        last_stage = stages[-1]
                        yield None, None, None, None, last_stage + ' Puede tardar varios minutos; no hace falta volver a pulsar.'
                if process.returncode:
                    raise ValueError(f'La reconstrucción local falló. Diagnóstico guardado en {folder / "proceso.log"}')
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        info = json.loads((folder / 'resultado.json').read_text(encoding='utf-8'))
        dimensions = ' × '.join(f'{v:.2f}' for v in info['dimensions'])
        status = (f'**Objeto completo sin placa:** {dimensions} mm · {info["faces"]:,} triángulos. '
                  f'**Estanca:** {"sí" if info["watertight"] else "no"} · **Piezas:** {info["parts"]}.\n\n'
                  'La cara oculta es estimada. GLB conserva colores; STL solo geometría. Revisa el modelo antes de imprimir.')
        yield str(folder / 'objeto-recortado.png'), str(folder / 'objeto.glb'), str(folder / 'objeto.stl'), str(folder / 'objeto.glb'), status
    except (ValueError, OSError) as exc:
        yield None, None, None, None, str(exc)
