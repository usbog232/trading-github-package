from size_utils import quantize_down


def test_quantize_down():
    assert quantize_down(0.0045908412, 4) == 0.0045
