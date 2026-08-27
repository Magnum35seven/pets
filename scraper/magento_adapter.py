"""
Generic adapter for any Magento 2 storefront.

Magento 2 sites expose a GraphQL endpoint at `/graphql` that the storefront
itself uses to render product listings — it's public and unauthenticated
for catalog browsing by design (that's how anonymous shoppers see products
without logging in), which makes it a much friendlier target than a
reverse-engineered internal search API.

Confirm a store is really Magento (and that /graphql is reachable) with:
    curl -s -X POST https://{domain}/graphql \\
      -H "Content-Type: application/json" \\
      -d '{"query":"{ products(search:\\"dog food\\", pageSize:1) { items { name } } }"}'

If that returns JSON with product data, this adapter should work as-is.
If it 404s or errors, the store either isn't Magento or has disabled
public GraphQL introspection/queries, and needs a custom adapter instead.
"""

import requests

from base import compute_unit_price, now_iso, polite_sleep

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

QUERY = """
query SearchProducts($search: String!, $pageSize: Int!, $currentPage: Int!) {
  products(search: $search, pageSize: $pageSize, currentPage: $currentPage) {
    total_count
    items {
      name
      sku
      url_key
      brand: manufacturer
      small_image { url }
      price_range {
        minimum_price {
          regular_price { value }
          final_price { value }
        }
      }
      stock_status
    }
  }
}
"""


def _extract(item, domain, store_id, store_name, category):
    title = item.get("name", "")
    price_range = (item.get("price_range") or {}).get("minimum_price", {})
    regular = (price_range.get("regular_price") or {}).get("value")
    final = (price_range.get("final_price") or {}).get("value")

    unit_price, basis = compute_unit_price(final or regular, title)

    return {
        "store": store_id,
        "store_name": store_name,
        "title": title,
        "brand": item.get("brand"),
        "price": final or regular,
        "compare_at_price": regular if regular and final and regular > final else None,
        "currency": "AUD",
        "unit_price": unit_price,
        "unit_price_basis": basis,
        "url": f"https://{domain}/{item.get('url_key', '')}.html",
        "image": (item.get("small_image") or {}).get("url"),
        "sku": item.get("sku"),
        "in_stock": item.get("stock_status") == "IN_STOCK",
        "category": category,
        "scraped_at": now_iso(),
    }


def fetch_products(domain, store_id, store_name, search_term="dog food",
                    category="pet-food", page_size=48, max_pages=15,
                    sleep_seconds=1.0):
    """
    Search a Magento store's public GraphQL catalog for a term (e.g. "dog
    food", "cat food") and return normalised product dicts. Run once per
    search term you care about — Magento's GraphQL search doesn't have a
    "give me a whole category" shortcut as clean as Shopify's collection
    feed, so search terms stand in for categories here.
    """
    results = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    url = f"https://{domain}/graphql"

    for page in range(1, max_pages + 1):
        body = {
            "query": QUERY,
            "variables": {"search": search_term, "pageSize": page_size, "currentPage": page},
        }
        resp = session.post(url, json=body, timeout=20)
        if resp.status_code == 404 and page == 1:
            raise RuntimeError(
                f"{domain} returned 404 on /graphql — this store may not be "
                f"Magento, or has GraphQL disabled. Needs a custom adapter."
            )
        resp.raise_for_status()
        payload = resp.json()

        if "errors" in payload:
            raise RuntimeError(f"{domain} GraphQL errors: {payload['errors']}")

        items = (payload.get("data", {}).get("products", {}) or {}).get("items", [])
        if not items:
            break

        for item in items:
            results.append(_extract(item, domain, store_id, store_name, category))

        polite_sleep(sleep_seconds)

    return results
