#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime

# Import store adapters
import shopify_adapter
import magento_adapter
import coles_adapter
import woolworths_adapter

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "stores_config.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "latest.json")

ADAPTER_MAP = {
    "shopify": shopify_adapter,
    "shopify_unconfirmed": shopify_adapter,
    "magento": magento_adapter,
    "magento_unconfirmed": magento_adapter,
    "coles": coles_adapter,
    "woolworths": woolworths_adapter,
}

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("stores", data)

def load_previous_data():
    """Loads existing product history from the output file if it exists."""
    if not os.path.exists(OUTPUT_PATH):
        return {}
    
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            items = json.load(f)
            # Map item ID or URL to its existing price history
            return {
                item.get("id", item.get("url")): item.get("price_history", [])
                for item in items
                if isinstance(item, dict)
            }
    except Exception as e:
        print(f"Warning: Could not read previous latest.json ({e}). Starting fresh.")
        return {}

def main():
    stores = load_config()
    print(f"Loaded {len(stores)} store configurations.")

    previous_histories = load_previous_data()
    today_str = datetime.now().strftime("%Y-%m-%d")

    all_products = []

    for store in stores:
        if not store.get("enabled", True):
            print(f"Skipping disabled store: {store.get('name', 'Unknown')}")
            continue

        platform = store.get("platform", "")
        adapter = ADAPTER_MAP.get(platform)

        if not adapter:
            print(f"No adapter found for platform '{platform}' in store '{store.get('name')}'")
            continue

        print(f"Scraping store: {store.get('name')} ({platform})...")
        try:
            products = adapter.scrape_store(store)
            print(f"  -> Found {len(products)} products.")
            all_products.extend(products)
        except Exception as e:
            print(f"  -> Error scraping {store.get('name')}: {e}")

        time.sleep(1)

    # Process price tracking and keep only the last 3 history snapshots
    processed_products = []
    for item in all_products:
        item_key = item.get("id", item.get("url"))
        current_price = item.get("price")

        # Fetch existing history or initialize empty
        history = previous_histories.get(item_key, [])

        # Avoid appending duplicate records if scraped multiple times on the same date
        if not history or history[-1].get("date") != today_str:
            history.append({
                "date": today_str,
                "price": current_price
            })
        else:
            history[-1]["price"] = current_price

        # Limit to the 3 most recent historical records
        history = history[-3:]
        item["price_history"] = history

        # Calculate price delta relative to the previous run
        if len(history) >= 2:
            prev_price = history[-2]["price"]
            item["previous_price"] = prev_price
            item["price_change"] = round(current_price - prev_price, 2)
        else:
            item["previous_price"] = current_price
            item["price_change"] = 0.0

        processed_products.append(item)

    print(f"\nTotal products scraped: {len(processed_products)}")

    # Save enriched dataset to frontend target path
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(processed_products, f, indent=2, ensure_ascii=False)

    print(f"Successfully saved output to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
