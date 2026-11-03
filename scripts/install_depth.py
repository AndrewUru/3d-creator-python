"""Download free model once; generation afterwards is entirely offline."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    env = ROOT / ".venv-ai"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "torch==2.6.0", "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "transformers==4.48.3", "numpy==1.26.4", "pillow==10.4.0"], check=True)
    code = '''
from pathlib import Path
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
import sys
target = Path(sys.argv[1])
name = "depth-anything/Depth-Anything-V2-Small-hf"
processor = AutoImageProcessor.from_pretrained(name)
model = AutoModelForDepthEstimation.from_pretrained(name)
processor.save_pretrained(target)
model.save_pretrained(target)
(target / "ready.ok").write_text(name)
'''
    subprocess.run([str(python), "-c", code, str(ROOT / "models" / "depth-anything-v2-small")], check=True)
    print("Profundidad local instalada. Sin API, cuentas ni tokens.")


if __name__ == "__main__":
    main()
