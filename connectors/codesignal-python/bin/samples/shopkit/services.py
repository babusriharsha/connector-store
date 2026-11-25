"""Business services for ShopKit."""

from .utils import format_price, slugify


def calculate_total(items):
    """Calculate the total price of a list of items."""
    return sum(item.price for item in items)


def apply_discount(total, percent):
    """Apply a percentage discount to a total."""
    if percent < 0:
        return total
    return round(total * (1 - percent / 100), 2)


def legacy_discount(total):
    """Legacy discount kept for reference; nothing calls this any more."""
    return round(total * 0.9, 2)


def process_checkout(order, user, payment, inventory, options):
    # TODO: split process_checkout into smaller steps before it grows further
    # FIXME: retry logic below double-charges on a slow payment gateway
    if order is None:
        raise ValueError("order is required")
    if not user:
        raise ValueError("user is required")
    if user.get("blocked") or user.get("unverified"):
        raise ValueError("user cannot check out")
    total = 0
    for item in order.items:
        if item.price < 0:
            raise ValueError("negative price")
        elif item.price == 0:
            continue
        if item.name in inventory and inventory[item.name] > 0:
            total += item.price
        else:
            raise ValueError("out of stock")
    attempts = 0
    paid = False
    while attempts < 3 and not paid:
        attempts += 1
        try:
            paid = payment(total)
        except Exception:
            paid = False
        if paid:
            break
        if attempts == 2:
            total = apply_discount(total, 5)
    labels = [slugify(item.name) for item in order.items if item.name]
    express = options.get("express") if options else False
    surcharge = 10 if express and total < 100 else 0
    if payment and inventory and options:
        total += surcharge
    if total > 100 or express:
        total = apply_discount(total, 10)
    summary = format_price(total)
    return {"total": total, "formatted": summary, "labels": labels, "paid": paid}
