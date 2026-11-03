"""Respuestas simuladas exclusivamente para pruebas; no invocan Meshy."""
import httpx
import pytest
import trimesh
from PIL import Image
from imagen3d.providers import MeshyProvider, JobManager, ProviderError


def provider(handler):
    return MeshyProvider("test-not-a-real-key", httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize("code, message", [(400, "parámetros"), (401, "clave"), (402, "créditos"), (403, "permiso"), (404, "encuentra"), (429, "Límite"), (500, "disponible")])
def test_http_errors(code, message):
    p = provider(lambda request: httpx.Response(code))
    with pytest.raises(ProviderError, match=message):
        p.retrieve("test-id")


def test_payload_and_deduplication(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer test-not-a-real-key"
        import json
        body = json.loads(request.content)
        assert body["image_url"].startswith("data:image/png;base64,")
        assert body["ai_model"] == "meshy-6"
        return httpx.Response(200, json={"result": "test-id"})
    p = provider(handler)
    manager = JobManager(p, tmp_path / "jobs.db")
    im = Image.new("RGBA", (20, 20), "white")
    assert manager.submit(im, True, True) == "test-id"
    assert manager.submit(im, True, True) == "test-id"
    assert len(requests) == 1
    assert JobManager(p, tmp_path / "jobs.db").submit(im, True, True) == "test-id"
    assert len(requests) == 1


@pytest.mark.parametrize("status, done", [("PENDING", False), ("IN_PROGRESS", False), ("FAILED", True), ("CANCELED", True)])
def test_task_states(tmp_path, status, done):
    manager = JobManager(provider(lambda req: httpx.Response(200, json={"status": status, "progress": 42})), tmp_path / "jobs.db")
    message, glb, stl, finished = manager.poll("test-id")
    assert "42%" in message and finished == done
    assert glb is None and stl is None


def test_success_download_and_stl(tmp_path):
    model = trimesh.creation.box().export(file_type="glb")
    def handler(request):
        if request.url.host == "assets.meshy.ai":
            assert "Authorization" not in request.headers
            return httpx.Response(200, content=model)
        return httpx.Response(200, json={"status": "SUCCEEDED", "model_urls": {"glb": "https://assets.meshy.ai/test.glb"}})
    manager = JobManager(provider(handler), tmp_path / "jobs.db")
    _, glb, stl, done = manager.poll("test-id")
    assert done and glb and stl
    assert trimesh.load(stl).extents[0] == pytest.approx(1000)


def test_timeout_does_not_repeat_post(tmp_path):
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("simulated timeout")
    manager = JobManager(provider(handler), tmp_path / "jobs.db")
    im = Image.new("RGBA", (20, 20))
    with pytest.raises(ProviderError, match="contactar"):
        manager.submit(im, True, True)
    with pytest.raises(ProviderError, match="sin confirmación"):
        manager.submit(im, True, True)
    assert len(requests) == 1


def test_consent_missing_key_and_untrusted_url(tmp_path):
    manager = JobManager(provider(lambda req: pytest.fail("Unexpected network")), tmp_path / "jobs.db")
    with pytest.raises(ProviderError, match="Confirma"):
        manager.submit(Image.new("RGBA", (20, 20)), False, False)
    with pytest.raises(ProviderError, match="MESHY_API_KEY"):
        MeshyProvider("").retrieve("test-id")
    with pytest.raises(ProviderError, match="no permitida"):
        manager.provider.download("http://127.0.0.1/private", tmp_path / "x")


def test_malformed_and_unknown_status(tmp_path):
    p = provider(lambda req: httpx.Response(200, content=b"bad-json"))
    with pytest.raises(ProviderError, match="Respuesta"):
        p.retrieve("test-id")
    manager = JobManager(provider(lambda req: httpx.Response(200, json={"status": "OTHER"})), tmp_path / "jobs.db")
    with pytest.raises(ProviderError, match="desconocido"):
        manager.poll("test-id")
