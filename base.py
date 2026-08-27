"""
Shared schema + helpers for all store adapters.

Every adapter's `fetch_products()` must yield/return a list of dicts matching
this shape, so the frontend never needs to know which store a product came
from beyond the `store` field.
"""

import re
import time
from datetime import datetime, timezone

# ---- Canonical product schema -------------------------------------------
# {
#   "store":            "petstock"            (short slug, matches stores_config.json id)
#   "store_name":        "PETstock"            (display name)
#   "title":             "Advance Adult Dog Chicken 15kg"
#   "brand":              "Advance" | None
#   "price":              84.99                (current selling price, AUD)
#   "compare_at_price":   99.99 | None          (was-price, if on special)
#   "currency":           "AUD"
#   "weight_value":       15.0 | None
#   "weight_unit":        "kg" | "g" | "L" | "ml" | None
#   "unit_price":         5.666  | None         (price per kg or per L, for comparison)
#   "unit_price_basis":   "kg" | "L" | None
#   "url":                "https://..."
#   "image":              "https://..." | None
#   "sku":                "..." | None
#   "in_stock":           True | False | None
#   "category":           "dog-food" | "cat-food" | ...
#   "scraped_at":         "2026-08-26T00:00:00+00:00"
# }


WEIGHT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>kg|g|l|ml|litre|litres)\b",
    re.IGNORECASE,
)

# normalise messy unit spellings to a canonical short form
_UNIT_MAP = {
    "kg": "kg",
    "g": "g",
    "l": "L",
    "litre": "L",
    "litres": "L",
    "ml": "ml",
}


def parse_weight(title: str):
    """
    Pull a pack size out of a free-text product title.
    Returns (value: float, unit: str) or (None, None) if nothing matched.
    Picks the LAST match in the string, since pack size is usually
    quoted at the end of the title (brand/flavour comes first).
    """
    matches = list(WEIGHT_RE.finditer(title or ""))
    if not matches:
        return None, None
    m = matches[-1]
    value = float(m.group("value"))
    unit = _UNIT_MAP.get(m.group("unit").lower())
    return value, unit


def to_base_unit(value, unit):
    """
    Convert a (value, unit) pair to a common comparison basis:
    weight -> kg, volume -> L. Returns (base_value, basis) or (None, None).
    """
    if value is None or unit is None:
        return None, None
    if unit == "kg":
        return value, "kg"
    if unit == "g":
        return value / 1000.0, "kg"
    if unit == "L":
        return value, "L"
    if unit == "ml":
        return value / 1000.0, "L"
    return None, None


def compute_unit_price(price, title):
    """
    Given a shelf price and the product title, return (unit_price, basis).
    unit_price is price per kg (for weight products) or per L (for liquids).
    """
    value, unit = parse_weight(title)
    base_value, basis = to_base_unit(value, unit)
    if not base_value or not price:
        return None, None
    return round(price / base_value, 3), basis


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def polite_sleep(seconds=1.0):
    """Every adapter should sleep between paginated requests — this is a
    small, deliberately boring catalogue (pet food only), not a firehose."""
    time.sleep(seconds)
