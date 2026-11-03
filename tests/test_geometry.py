import numpy as np
import pytest
import trimesh
from PIL import Image
from imagen3d.geometry import mask_image, build_mesh, export_mesh, read_image, contours_to_polygons


def rectangle():
    mask = np.zeros((100, 120), dtype=np.uint8)
    mask[10:90, 10:110] = 255
    return mask


def test_simple_and_export_scale(tmp_path):
    mesh, _ = build_mesh(rectangle(), width=80, thickness=6)
    assert mesh.is_volume and mesh.is_watertight
    assert mesh.extents[0] == pytest.approx(80)
    assert mesh.extents[1] == pytest.approx(80 * 79 / 99)
    assert mesh.extents[2] == pytest.approx(6)
    stl, glb = export_mesh(mesh, tmp_path)
    loaded_stl = trimesh.load(stl)
    loaded_glb = trimesh.load(glb, force="scene").to_mesh()
    assert loaded_stl.is_volume and loaded_glb.is_volume
    np.testing.assert_allclose(loaded_stl.extents, loaded_glb.extents * 1000, rtol=1e-5)


def test_hole_preserved():
    mask = rectangle()
    mask[30:70, 40:80] = 0
    shapes, _ = contours_to_polygons(mask)
    assert len(shapes[0].interiors) == 1
    mesh, _ = build_mesh(mask)
    assert mesh.is_volume and mesh.euler_number == 0
    assert mesh.volume < np.prod(mesh.extents)


def test_disconnected_and_union_base():
    mask = rectangle()
    mask[:, 50:70] = 0
    mesh, _ = build_mesh(mask)
    assert len(mesh.split()) == 2
    joined, _ = build_mesh(mask, base=True)
    assert joined.is_volume
    assert len(joined.split()) == 1
    assert joined.extents[0] == pytest.approx(100)


def test_transparent_empty():
    mask = mask_image(Image.new("RGBA", (100, 100), (0, 0, 0, 0)))
    assert not mask.any()
    with pytest.raises(ValueError, match="vacía"):
        build_mesh(mask)


def test_too_small_contour():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[5, 5] = 255
    with pytest.raises(ValueError, match="área"):
        build_mesh(mask)


def test_nested_island():
    mask = rectangle()
    mask[20:80, 20:100] = 0
    mask[40:60, 40:80] = 255
    mesh, _ = build_mesh(mask)
    assert len(mesh.split()) == 2 and mesh.is_volume


def test_input_content_and_limits(tmp_path):
    invalid = tmp_path / "fake.png"
    invalid.write_text("not an image")
    with pytest.raises(ValueError):
        read_image(invalid)
    gif = tmp_path / "fake.jpg"
    Image.new("RGB", (20, 20)).save(gif, format="GIF")
    with pytest.raises(ValueError, match="PNG o JPEG"):
        read_image(gif)
    Image.new("RGB", (3, 3)).save(invalid)
    with pytest.raises(ValueError, match="8 × 8"):
        read_image(invalid)


def test_threshold_inversion_and_cleanup():
    image = Image.new("RGB", (50, 50), "white")
    image.paste("black", (10, 10, 40, 40))
    a = mask_image(image, min_area=1)
    b = mask_image(image, invert=True, min_area=1)
    assert np.all(a.astype(int) + b == 255)
    assert not mask_image(image, min_area=1000).any()
