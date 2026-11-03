from imagen3d.objects import generate_object


def test_reject_invalid_size_before_starting_worker():
    results = list(generate_object(None, 0, 128))
    assert len(results) == 1
    assert all(value is None for value in results[0][:4])
    assert 'Tamaño' in results[0][-1]


def test_missing_input_does_not_start_worker():
    results = list(generate_object(None, 100, 128))
    assert len(results) == 1
    assert 'Sube una imagen' in results[0][-1]
