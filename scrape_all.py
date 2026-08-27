"""
Runs every enabled store adapter, writes:
  data/latest.json              - current snapshot, what the PWA reads
  data/history/YYYY-MM-DD.json  - dated snapshot, for price-history charts
  data/price_changes.json       - biggest movers vs the previous snapshot

Run this on a schedule (see .github/workflows/scrape.yml) rather than
per-user-request — the frontend reads the static JSON files it produces,
it never calls the stores directly.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Data lives under frontend/data so GitHub Pages (which serves the frontend/
# folder) can fetch it via a plain relative path — no separate API needed.
DATA_DIR = ROOT / "frontend" / "data"
HISTORY_DIR = DATA_DIR / "history"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import shopify_adapter, magento_adapter, coles_adapter, woolworths_adapter  # noqa: E402


def load_config():
    with open(Path(__file__).resolve().parent / "stores_config.json") as f:
        return json.load(f)["stores"]


def run_store(store):
    platform = store["platform"]
    store_id = store["id"]

    if platform in ("shopify", "shopify_unconfirmed"):
        return shopify_adapter.fetch_products(
            domain=store["domain"],
            store_id=store_id,
            store_name=store["name"],
            collection_handle=store.get("collection_handle"),
        )
    if platform in ("magento", "magento_unconfirmed"):
        return magento_adapter.fetch_products(
            domain=store["domain"],
            store_id=store_id,
            store_name=store["name"],
            search_term=store.get("search_term", "dog food"),
        )
    if store_id == "woolworths":
        return woolworths_adapter.fetch_products()
    if store_id == "coles":
        return coles_adapter.fetch_products()

    raise ValueError(f"No adapter wired up for store '{store_id}' (platform={platform})")


def compute_price_changes(previous_products, current_products, threshold_pct=10.0):
    """Flag products whose price moved by more than threshold_pct since the
    last snapshot — this powers the 'big price drops or rises' feature."""
    prev_by_key = {(p["store"], p.get("sku") or p.get("url")): p for p in previous_products}
    changes = []

    for prod in current_products:
        key = (prod["store"], prod.get("sku") or prod.get("url"))
        prev = prev_by_key.get(key)
        if not prev or not prev.get("price") or not prod.get("price"):
            continue
        old_price, new_price = prev["price"], prod["price"]
        if old_price == 0:
            continue
        pct_change = round((new_price - old_price) / old_price * 100, 1)
        if abs(pct_change) >= threshold_pct:
            changes.append({
                "store": prod["store"],
                "store_name": prod["store_name"],
                "title": prod["title"],
                "url": prod["url"],
                "old_price": old_price,
                "new_price": new_price,
                "pct_change": pct_change,
                "direction": "drop" if pct_change < 0 else "rise",
            })

    changes.sort(key=lambda c: c["pct_change"])
    return changes


def main():
    DATA_DIR.mkdir(exist_ok=True)
    HISTORY_DIR.mkdir(exist_ok=True)

    config = load_config()
    all_products = []
    errors = []

    for store in config:
        if not store.get("enabled"):
            continue
        print(f"Scraping {store['name']} ({store['id']})...")
        try:
            products = run_store(store)
            print(f"  -> {len(products)} products")
            all_products.extend(products)
        except Exception as e:
            print(f"  !! FAILED: {e}")
            errors.append({"store": store["id"], "error": str(e)})

    # Load previous snapshot (if any) before we overwrite it, for price-diffing
    previous_products = []
    latest_path = DATA_DIR / "latest.json"
    if latest_path.exists():
        with open(latest_path) as f:
            previous_products = json.load(f).get("products", [])

    snapshot = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "product_count": len(all_products),
        "errors": errors,
        "products": all_products,
    }

    with open(latest_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    today_path = HISTORY_DIR / f"{date.today().isoformat()}.json"
    with open(today_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    changes = compute_price_changes(previous_products, all_products)
    with open(DATA_DIR / "price_changes.json", "w") as f:
        json.dump({"computed_at": datetime.now(timezone.utc).isoformat(), "changes": changes}, f, indent=2)

    print(f"\nDone. {len(all_products)} products, {len(errors)} store(s) failed, "
          f"{len(changes)} notable price change(s).")


if __name__ == "__main__":
    main()
