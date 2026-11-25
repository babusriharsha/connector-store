"""Tests for ShopKit services."""

from shopkit.models import Product
from shopkit.services import apply_discount, calculate_total


def test_calculate_total():
    items = [Product("Mug", 10), Product("Tea", 5)]
    assert calculate_total(items) == 15


def test_apply_discount():
    assert apply_discount(100, 10) == 90.0
