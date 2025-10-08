"""Tests for main module."""

from src.main import add


def test_add() -> None:
    """Test add function with positive integers."""
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
    assert add(100, 200) == 300
