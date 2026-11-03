import numpy as np
import pytest
import trimesh
from PIL import Image

from imagen3d.relief import build_relief, prepare_heights
from imagen3d.geometry import export_mesh


def test_ramp_volume_and_export(tmp_path):
    heights = np.tile(np.linspace(0, 1, 12), (8, 1))
    mesh = build_relief(heights, width=100, relief=6, base=2, aspect=0.5)
    assert mesh.is_volume and mesh.is_watertight and mesh.is_winding_consistent
    assert mesh.euler_number == 2
    assert len(mesh.split()) == 1
    np.testing.assert_allclose(mesh.extents, [100, 50, 8])
    assert mesh.volume == pytest.approx(100 * 50 * (2 + 3))
    stl, glb = export_mesh(mesh, tmp_path)
    a = trimesh.load(stl)
    b = trimesh.load(glb, force="scene").to_mesh()
    assert a.is_volume and b.is_volume
    np.testing.assert_allclose(a.extents, b.extents * 1000, rtol=1e-5)


def test_map_inversion_and_alpha():
    im = Image.fromarray(np.tile(np.arange(256, dtype=np.uint8), (32, 1)))
    a = prepare_heights(im, resolution=256, smooth=0)
    b = prepare_heights(im, resolution=256, smooth=0, invert=True)
    np.testing.assert_allclose(a+b, 1)
    assert a[0, 0] == 0 and a[0, -1] == 1
    transparent = im.convert("RGBA")
    transparent.putalpha(Image.fromarray(np.tile(np.r_[np.zeros(128), np.full(128, 255)].astype(np.uint8), (32, 1))))
    assert not prepare_heights(transparent, resolution=256, smooth=0, invert=True)[:, :128].any()


def test_flat_and_narrow_meshes():
    for shape in [(2, 32), (32, 2), (8, 8)]:
        mesh = build_relief(np.zeros(shape))
        assert mesh.is_volume and mesh.is_watertight
        assert mesh.volume == pytest.approx(100 * 100 * 2)


def test_invalid_and_empty():
    for values in [np.full((4, 4), np.nan), np.ones((1, 8)), np.full((4, 4), -1)]:
        with pytest.raises(ValueError):
            build_relief(values)
    with pytest.raises(ValueError):
        prepare_heights(Image.new("RGBA", (32, 32), (0, 0, 0, 0)))


def test_relative_depth_and_gamma():
    image = Image.new("RGB", (32, 32))
    depth = np.tile(np.linspace(100, 200, 32), (32, 1))
    a = prepare_heights(image, depth, resolution=32, smooth=0)
    b = prepare_heights(image, depth, resolution=32, smooth=0, gamma=2)
    assert a.min() == 0 and a.max() == 1
    np.testing.assert_allclose(b, a*a)
