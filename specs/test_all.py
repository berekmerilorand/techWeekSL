import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.string_reverser import reverse_string


def test_reverse_string():
    assert reverse_string("hello") == "olleh"
