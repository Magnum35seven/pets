"""
Woolworths adapter — HIGHER MAINTENANCE, VERIFY BEFORE RELYING ON IT.

Woolworths' storefront calls an internal API (roughly
`https://www.woolworths.com.au/apis/ui/Search/products`) that isn't publicly
documented and requires a valid session: a browser first loads the site to
get cookies (incl. a bot-detection token) before the search endpoint will
respond with real data instead of a 403.

This is meaningfully more fragile than the Shopify feed:
- endpoint paths and required headers change periodically
- needs a real session/cookie jar, not just a bare request
- aggressive polling WILL get the IP flagged faster than a small Shopify store

Recommended approach:
1. Restrict this adapter to the pet-food category only (small slice of
   their catalogue = low request volume = lower risk).
2. Run it much less frequently than the Shopify stores (e.g. every few
   days, not daily) until you've watched it behave reliably.
3. Expect to come back and fix selectors/headers when this breaks — treat
   it as the highest-maintenance adapter in the project, by design.

The function below is a starting skeleton, not a guaranteed-working
scraper: the request shape needs to be captured fresh from the browser's
network tab (DevTools -> Network -> XHR) against the live site, since
publishing exact working payloads here would go stale immediately and
isn't something to build against sight-unseen.
"""

import requests

from .base import compute_unit_price, now_iso

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SEARCH_URL = "https://www.woolworths.com.au/apis/ui/Search/products"


def fetch_products(category_slug="pet", store_id="woolworths",
                    store_name="Woolworths", page_size=36, max_pages=5):
    """
    Skeleton only. Before running this for real:
    1. Open woolworths.com.au in a browser, search "dog food".
    2. In DevTools Network tab, find the XHR request to /apis/ui/Search/products.
    3. Copy its exact request payload (JSON body) and required headers into
       this function — they change over time, so don't assume last year's
       shape still works.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Warm the session first — Woolworths' bot detection generally requires
    # cookies from a normal page load before the API will respond.
    session.get("https://www.woolworths.com.au/", timeout=20)

    results = []
    for page in range(1, max_pages + 1):
        body = {
            "Filters": [],
            "IsSpecial": False,
            "Location": f"/shop/search/products?searchTerm={category_slug}",
            "PageNumber": page,
            "PageSize": page_size,
            "SearchTerm": category_slug,
            "SortType": "TraderRelevance",
        }
        resp = session.post(SEARCH_URL, json=body, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Woolworths search returned {resp.status_code} — session/headers "
                f"likely need updating (see module docstring)."
            )
        payload = resp.json()
        bundles = payload.get("Products", []) or payload.get("Bundles", [])
        if not bundles:
            break

        for bundle in bundles:
            product = bundle.get("Products", [bundle])[0] if "Products" in bundle else bundle
            title = product.get("Name") or product.get("DisplayName", "")
            price = product.get("Price")
            was_price = product.get("WasPrice")
            unit_price, basis = compute_unit_price(price, title)

            results.append({
                "store": store_id,
                "store_name": store_name,
                "title": title,
                "brand": product.get("Brand"),
                "price": price,
                "compare_at_price": was_price if was_price and was_price > (price or 0) else None,
                "currency": "AUD",
                "unit_price": unit_price,
                "unit_price_basis": basis,
                "url": f"https://www.woolworths.com.au/shop/productdetails/{product.get('Stockcode')}",
                "image": (product.get("MediumImageFile") or product.get("SmallImageFile")),
                "sku": product.get("Stockcode"),
                "in_stock": product.get("IsAvailable"),
                "category": "pet-food",
                "scraped_at": now_iso(),
            })

    return results
