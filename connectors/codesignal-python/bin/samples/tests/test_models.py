"""Tests for ShopKit models."""

from shopkit.models import Order, Product


def test_product_price_with_tax():
    product = Product("Mug", 100)
    assert product.price_with_tax(0.1) == 110.0


def test_order_total():
    order = Order([Product("Mug", 10), Product("Tea", 5)])
    assert order.total() == 15
