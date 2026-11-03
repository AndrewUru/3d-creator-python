"""Instalación explícita; nunca se ejecuta al arrancar la interfaz."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "runtime" / "TripoSR"
REVISION = "107cefdc244c39106fa830359024f6a2f1c78871"
WEIGHT_HASH = "429e2c6b22a0923967459de24d67f05962b235f79cde6b032aa7ed2ffcd970ee"


def download(url, target, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not expected or checksum(target) == expected):
        print(f"Disponible: {target.name}", flush=True)
        return
    temporary = target.with_suffix(target.suffix + ".part")
    print(f"Descargando {target.name}…", flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as out:
        total = 0
        while chunk := response.read(4 * 1024 * 1024):
            out.write(chunk)
            total += len(chunk)
            if total % (128 * 1024 * 1024) == 0:
                print(f"  {total // 1024 // 1024} MiB recibidos", flush=True)
    if expected and checksum(temporary) != expected:
        raise RuntimeError("La suma SHA256 del modelo no coincide; no se instalará.")
    temporary.replace(target)


def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def patch_cpu():
    """Sustituye solo la extracción CUDA por marching cubes CPU de scikit-image."""
    path = REPO / "tsr" / "models" / "isosurface.py"
    source = path.read_text(encoding="utf-8")
    source = source.replace("from torchmcubes import marching_cubes", """from skimage.measure import marching_cubes as sk_marching_cubes

def marching_cubes(level, threshold):
    vertices, faces, _, _ = sk_marching_cubes(level.detach().cpu().numpy(), threshold)
    # Upstream reverses xyz after calling torchmcubes; undo that convention here.
    return torch.from_numpy(vertices[:, [2, 1, 0]].copy()), torch.from_numpy(faces.copy().astype(np.int64))
""")
    path.write_text(source, encoding="utf-8")
    path = REPO / "tsr" / "models" / "tokenizers" / "image.py"
    source = path.read_text(encoding="utf-8")
    old = '''hf_hub_download(
                    repo_id=self.cfg.pretrained_model_name_or_path,
                    filename="config.json",
                )'''
    source = source.replace(old, '__import__("os").environ["IMAGEN3D_DINO_CONFIG"]')
    path.write_text(source, encoding="utf-8")
    path = REPO / "tsr" / "system.py"
    source = path.read_text(encoding="utf-8").replace('torch.load(weight_path, map_location="cpu")', 'torch.load(weight_path, map_location="cpu", weights_only=True, mmap=True)')
    source = source.replace('model.load_state_dict(ckpt)', 'model.load_state_dict(ckpt, assign=True)')
    path.write_text(source, encoding="utf-8")


def main():
    env = ROOT / ".venv-tripo"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "torch==2.6.0", "torchvision==0.21.0", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-ai.txt")], check=True)
    if not REPO.exists():
        subprocess.run(["git", "clone", "https://github.com/VAST-AI-Research/TripoSR.git", str(REPO)], check=True)
    actual = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    if actual != REVISION:
        subprocess.run(["git", "-C", str(REPO), "checkout", REVISION], check=True)
    patch_cpu()
    model = ROOT / "models" / "TripoSR"
    download("https://huggingface.co/stabilityai/TripoSR/resolve/main/config.yaml", model / "config.yaml")
    download("https://huggingface.co/stabilityai/TripoSR/resolve/main/model.ckpt", model / "model.ckpt", WEIGHT_HASH)
    download("https://huggingface.co/facebook/dino-vitb16/resolve/main/config.json", model / "dino-config.json")
    # Small optional foreground model, 4.7 MB; inference remains entirely local.
    download("https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx", ROOT / "models" / "rembg" / "u2netp.onnx")
    (model / "installed.ok").write_text(REVISION, encoding="utf-8")
    print("IA local instalada. Inicia app.py desde el entorno básico.", flush=True)


if __name__ == "__main__":
    main()
