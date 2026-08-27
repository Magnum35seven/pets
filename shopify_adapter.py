"""
Generic adapter for any Shopify storefront.

Shopify exposes a public, unauthenticated JSON feed for every store at:
    https://{domain}/products.json?limit=250&page=N
or, scoped to one collection (much smaller / more polite):
    https://{domain}/collections/{handle}/products.json?limit=250&page=N

This works for PETstock, Budget Pet Products, VetSupply, and most other
mid-size AU pet retailers *if* they run on Shopify — confirm this per-store
before relying on it (see README "Confirming a store's platform"). If a
store returns 404 on this path, it's not on Shopify (or has disabled the
feed) and needs its own adapter.
"""

import requests

from .base import compute_unit_price, now_iso, polite_sleep

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _product_url(handle, domain):
    return f"https://{domain}/products/{handle}"


def _extract(product, domain, store_id, store_name, category):
    variant = (product.get("variants") or [{}])[0]
    price = float(variant.get("price") or 0) or None
    compare_at = variant.get("compare_at_price")
    compare_at = float(compare_at) if compare_at else None
    title = product.get("title", "")

    unit_price, basis = compute_unit_price(price, title)

    image = None
    images = product.get("images") or []
    if images:
        image = images[0].get("src")

    return {
        "store": store_id,
        "store_name": store_name,
        "title": title,
        "brand": product.get("vendor"),
        "price": price,
        "compare_at_price": compare_at if compare_at and compare_at > (price or 0) else None,
        "currency": "AUD",
        "unit_price": unit_price,
        "unit_price_basis": basis,
        "url": _product_url(product.get("handle", ""), domain),
        "image": image,
        "sku": variant.get("sku"),
        "in_stock": variant.get("available"),
        "category": category,
        "scraped_at": now_iso(),
    }


def fetch_products(domain, store_id, store_name, category="pet-food",
                    collection_handle=None, max_pages=20, page_size=250,
                    sleep_seconds=1.0):
    """
    Pull every product from a Shopify store (optionally scoped to one
    collection). Returns a list of normalised product dicts.
    """
    results = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    if collection_handle:
        base_path = f"https://{domain}/collections/{collection_handle}/products.json"
    else:
        base_path = f"https://{domain}/products.json"

    for page in range(1, max_pages + 1):
        resp = session.get(base_path, params={"limit": page_size, "page": page}, timeout=20)
        if resp.status_code == 404 and page == 1:
            raise RuntimeError(
                f"{domain} returned 404 on {base_path} — this store is likely "
                f"not on Shopify (or the public feed is disabled). Needs a "
                f"custom adapter instead."
            )
        resp.raise_for_status()
        payload = resp.json()
        products = payload.get("products", [])
        if not products:
            break

        for product in products:
            results.append(_extract(product, domain, store_id, store_name, category))

        polite_sleep(sleep_seconds)

    return results
