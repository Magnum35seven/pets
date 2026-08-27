"""
Coles adapter — HIGHER MAINTENANCE, VERIFY BEFORE RELYING ON IT.

Same situation as woolworths_adapter.py: Coles' storefront is backed by an
internal API under `www.coles.com.au/api/...` that requires session cookies
and isn't publicly documented. It changes shape periodically and is
actively defended against high-volume scraping.

Do NOT copy last year's known endpoint/header shape from a blog post and
assume it still works — capture it fresh from your own browser's DevTools
Network tab (search "dog food" on coles.com.au, find the XHR call) and
fill in SEARCH_URL / the request shape below before running this for real.

Same mitigations as Woolworths apply: pet-food category only, low request
volume, infrequent runs, expect occasional breakage and fixes.
"""

import requests

from base import compute_unit_price, now_iso

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Placeholder — replace with the real endpoint captured from DevTools.
SEARCH_URL = "https://www.coles.com.au/api/search/products"


def fetch_products(search_term="dog food", store_id="coles",
                    store_name="Coles", page_size=48, max_pages=5):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.get("https://www.coles.com.au/", timeout=20)  # warm cookies

    results = []
    for page in range(1, max_pages + 1):
        params = {"q": search_term, "page": page, "pageSize": page_size}
        resp = session.get(SEARCH_URL, params=params, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Coles search returned {resp.status_code} — endpoint/session "
                f"needs updating (see module docstring)."
            )
        payload = resp.json()
        items = payload.get("results", []) or payload.get("products", [])
        if not items:
            break

        for item in items:
            title = item.get("name", "")
            price = (item.get("pricing") or {}).get("now")
            was = (item.get("pricing") or {}).get("was")
            unit_price, basis = compute_unit_price(price, title)

            results.append({
                "store": store_id,
                "store_name": store_name,
                "title": title,
                "brand": item.get("brand"),
                "price": price,
                "compare_at_price": was if was and was > (price or 0) else None,
                "currency": "AUD",
                "unit_price": unit_price,
                "unit_price_basis": basis,
                "url": f"https://www.coles.com.au/product/{item.get('slug', '')}",
                "image": item.get("imageUri"),
                "sku": item.get("sku") or item.get("id"),
                "in_stock": item.get("availability", True),
                "category": "pet-food",
                "scraped_at": now_iso(),
            })

    return results
