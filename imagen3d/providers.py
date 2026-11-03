"""Meshy real: tests use httpx.MockTransport; production never simulates output."""
from abc import ABC, abstractmethod
import base64
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import threading
from urllib.parse import urlparse

import httpx
import trimesh

from .storage import ROOT, new_folder


class ProviderError(ValueError):
    pass


class ImageTo3DProvider(ABC):
    @abstractmethod
    def create(self, image, textured): ...

    @abstractmethod
    def retrieve(self, task_id): ...

    @abstractmethod
    def download(self, url, target): ...


class MeshyProvider(ImageTo3DProvider):
    endpoint = "https://api.meshy.ai/openapi/v1/image-to-3d"

    def __init__(self, key, client=None):
        self.key = key
        self.client = client or httpx.Client(timeout=httpx.Timeout(60, connect=15), follow_redirects=False)

    def request(self, method, url, **kwargs):
        if not self.key:
            raise ProviderError("Falta configurar MESHY_API_KEY en el backend.")
        try:
            response = self.client.request(method, url, headers={"Authorization": f"Bearer {self.key}"}, **kwargs)
        except httpx.HTTPError:
            raise ProviderError("No se pudo contactar con Meshy. Si era un envío, comprueba tu panel antes de repetir: podría haberse cobrado.") from None
        errors = {400: "Meshy rechazó los parámetros o la imagen.", 401: "La clave de Meshy no es válida.",
                  402: "Meshy requiere un plan de pago y créditos suficientes.", 403: "La cuenta no tiene permiso.",
                  404: "Meshy no encuentra la tarea.", 429: "Límite de Meshy alcanzado. Espera antes de consultar de nuevo."}
        if response.status_code >= 400:
            raise ProviderError(errors.get(response.status_code, "Meshy no está disponible temporalmente. Consulta más tarde."))
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except ValueError:
            raise ProviderError("Respuesta no válida de Meshy.") from None

    def create(self, image, textured):
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        raw = buffer.getvalue()
        if len(raw) > 15 * 1024 * 1024:
            raise ProviderError("La imagen preparada supera 15 MB; reduce su resolución.")
        data = self.request("POST", self.endpoint, json={
            "image_url": "data:image/png;base64," + base64.b64encode(raw).decode(),
            "ai_model": "meshy-6", "should_texture": bool(textured), "target_formats": ["glb"],
        })
        task_id = data.get("result")
        if not isinstance(task_id, str) or not task_id or len(task_id) > 128 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in task_id):
            raise ProviderError("Meshy no devolvió un identificador válido. Comprueba el panel antes de repetir.")
        return task_id

    def retrieve(self, task_id):
        return self.request("GET", self.endpoint + "/" + task_id)

    def download(self, url, target):
        parsed = urlparse(url)
        # Only trust documented Meshy asset hosts, no arbitrary URLs or redirects.
        if parsed.scheme != "https" or not (parsed.hostname == "assets.meshy.ai" or (parsed.hostname or "").endswith(".meshy.ai")) or parsed.port not in (None, 443):
            raise ProviderError("El servidor devolvió una dirección de descarga no permitida.")
        try:
            with self.client.stream("GET", url) as response:
                response.raise_for_status()
                size = 0
                with open(target, "wb") as output:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 200 * 1024 * 1024:
                            raise ProviderError("El modelo supera el límite de descarga de 200 MB.")
                        output.write(chunk)
        except httpx.HTTPError:
            raise ProviderError("No se pudo descargar el modelo. Puedes volver a consultar sin generar otra tarea.") from None


class JobManager:
    """Serializes submissions and remembers uncertain sends across restarts."""
    def __init__(self, provider, ledger=None):
        self.provider = provider
        ROOT.mkdir(exist_ok=True)
        self.ledger = str(ledger or ROOT / "tasks.sqlite3")
        self.lock = threading.Lock()
        with sqlite3.connect(self.ledger) as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (digest TEXT PRIMARY KEY, task TEXT)")
        self.results = {}

    def submit(self, image, textured, consent):
        if not consent:
            raise ProviderError("Confirma el envío a Meshy y su posible coste antes de generar.")
        digest = hashlib.sha256(image.tobytes() + str(image.size).encode() + str(bool(textured)).encode() + b"meshy-6").hexdigest()
        with self.lock:
            with sqlite3.connect(self.ledger) as db:
                previous = db.execute("SELECT task FROM jobs WHERE digest=?", (digest,)).fetchone()
                if previous:
                    if previous[0]:
                        return previous[0]
                    raise ProviderError("Este envío quedó sin confirmación. Revisa el panel Meshy; no se repetirá automáticamente para evitar otro cobro.")
                db.execute("INSERT INTO jobs VALUES (?, NULL)", (digest,))
            task = self.provider.create(image, textured)
            with sqlite3.connect(self.ledger) as db:
                db.execute("UPDATE jobs SET task=? WHERE digest=?", (task, digest))
            return task

    def poll(self, task):
        if not task:
            return "Aún no hay ninguna tarea.", None, None, False
        with self.lock:
            if task in self.results:
                cached = self.results[task]
                if cached[1] and Path(cached[1]).exists():
                    return cached
                del self.results[task]
            data = self.provider.retrieve(task)
            status = data.get("status")
            labels = {"PENDING": "En cola", "IN_PROGRESS": "Generando", "SUCCEEDED": "Completada",
                      "FAILED": "Fallida", "CANCELED": "Cancelada"}
            if status not in labels:
                raise ProviderError("Meshy devolvió un estado desconocido; consulta de nuevo más tarde.")
            message = f"**{labels[status]}** · Tarea `{task}`"
            progress = data.get("progress")
            if isinstance(progress, (int, float)) and 0 <= progress <= 100:
                message += f" · Progreso comunicado por Meshy: {progress}%"
            if status in {"FAILED", "CANCELED"}:
                return message + " · Revisa los detalles en tu panel Meshy.", None, None, True
            if status != "SUCCEEDED":
                return message, None, None, False
            url = (data.get("model_urls") or {}).get("glb")
            if not url:
                raise ProviderError("La tarea terminó pero todavía no hay un GLB descargable.")
            folder = new_folder()
            glb = folder / "modelo-ia.glb"
            self.provider.download(url, glb)
            stl = None
            try:
                scene = trimesh.load(glb, force="scene")
                mesh = scene.to_mesh()
                if not len(mesh.faces):
                    raise ValueError("Empty mesh")
                mesh.apply_scale(1000)  # GLB meters -> STL millimeters, no inferred physical accuracy.
                stl = str(folder / "modelo-ia.stl")
                mesh.export(stl)
                message += f"\n\n{len(mesh.faces):,} triángulos · Estanca: {'sí' if mesh.is_watertight else 'no'}."
            except Exception:
                message += "\n\nNo se pudo convertir este GLB a STL. Descarga el original."
            message += "\n\nSTL sin texturas; escala estimada por IA, no dimensionalmente exacta. Revisa la imprimibilidad."
            result = (message, str(glb), stl, True)
            self.results[task] = result
            return result
