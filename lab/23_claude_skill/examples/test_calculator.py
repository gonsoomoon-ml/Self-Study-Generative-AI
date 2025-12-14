"""
Tests for the calculator module.
Run with: pytest test_calculator.py -v
"""

import pytest
from calculator import add, subtract, multiply, divide, calculate


class TestBasicOperations:
    """Test basic math operations."""

    def test_add(self):
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_subtract(self):
        assert subtract(5, 3) == 2
        assert subtract(0, 5) == -5

    def test_multiply(self):
        assert multiply(4, 5) == 20
        assert multiply(-2, 3) == -6
        assert multiply(0, 100) == 0

    def test_divide(self):
        assert divide(10, 2) == 5
        assert divide(7, 2) == 3.5

    def test_divide_by_zero(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)


class TestCalculateFunction:
    """Test the calculate dispatcher function."""

    def test_calculate_add(self):
        assert calculate('add', 2, 3) == 5

    def test_calculate_subtract(self):
        assert calculate('subtract', 10, 4) == 6

    def test_calculate_multiply(self):
        assert calculate('multiply', 3, 4) == 12

    def test_calculate_divide(self):
        assert calculate('divide', 20, 5) == 4

    def test_calculate_unknown_operation(self):
        with pytest.raises(ValueError, match="Unknown operation"):
            calculate('power', 2, 3)
