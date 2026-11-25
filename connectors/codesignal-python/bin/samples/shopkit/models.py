"""Data models for ShopKit."""


class Product:
    """A product for sale in the shop."""

    def __init__(self, name, price):
        self.name = name
        self.price = price

    def price_with_tax(self, rate):
        """Return the price including the given tax rate."""
        return round(self.price * (1 + rate), 2)


class Order:
    """A customer order holding a list of products."""

    def __init__(self, items):
        self.items = items

    def total(self):
        return sum(item.price for item in self.items)
