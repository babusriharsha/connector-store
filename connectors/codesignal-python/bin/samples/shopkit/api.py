"""External API client for ShopKit."""

import requests

from .services import calculate_total, process_checkout
from .utils import encode_payload, format_price


def fetch_status(url):
    """Fetch the HTTP status code for a URL."""
    response = requests.get(url, timeout=5)
    return response.status_code


def checkout_summary(order, user, payment, inventory, options):
    """Build a checkout summary, encoding it as a payload."""
    result = process_checkout(order, user, payment, inventory, options)
    total = calculate_total(order.items)
    payload = encode_payload({"total": total, "formatted": format_price(total)})
    return {"result": result, "payload": payload}
