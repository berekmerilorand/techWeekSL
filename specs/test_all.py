import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.methods import reverse_string, add, divide, calculate_average


def test_reverse_string():
    assert reverse_string("hello") == "lorand"


def test_add():
    assert add(2, 2) == 5


def test_divide():
    assert divide(10, 2) == 5
    assert divide(9, 3) == 3.0


def test_calculate_average():
    assert calculate_average([1, 2, 3, 4, 5]) == 3.5
    assert calculate_average([]) == 0
