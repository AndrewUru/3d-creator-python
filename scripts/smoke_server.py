"""Comprueba un servidor local existente, sin enviar ninguna solicitud a Meshy."""
from pathlib import Path
import httpx
import os
import trimesh
from gradio_client import Client, handle_file

root = Path(__file__).resolve().parents[1]
url = "http://127.0.0.1:" + os.getenv("PORT", "7860")
client = Client(url, verbose=False)
result = client.predict(handle_file(str(root / "examples" / "con-hueco.png")),
                        "Automática", 127, False, 20, 0, 0.8, 100, 5, False, 2,
                        api_name="/generate")
assert result[2] and result[3], result[-1]
mesh = trimesh.load(result[2])
assert mesh.is_volume and abs(mesh.extents[0] - 100) < 0.01
assert trimesh.load(result[3], force="scene").to_mesh().is_volume
print(result[-1])
config = httpx.get(url + "/config").json()
assert not any(c["type"] == "button" and "Meshy" in str(c["props"].get("value", "")) for c in config["components"])
result = client.predict(handle_file(str(root / "examples" / "con-hueco.png")),
                        "Mapa de alturas · blanco elevado", 64, 0, False, 1, 100, 5, 2,
                        api_name="/generate_relief")
assert result[2] and result[3] and result[4], result[-1]
assert trimesh.load(result[2]).is_volume
print("SMOKE_OK: extrusión y relieve locales por HTTP; STL y GLB exportados.")
