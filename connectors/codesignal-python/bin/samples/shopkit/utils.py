"""Helper utilities for ShopKit."""

import json
import os


def format_price(amount):
    """Format an amount as a price string."""
    return f"${amount:.2f}"


def slugify(text):
    return text.lower().replace(" ", "-")


def encode_payload(data):
    """Encode a dictionary as a JSON payload string."""
    return json.dumps(data)
