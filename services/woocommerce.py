"""WooCommerce REST API client with an explicit offline demo fallback."""
import os
from urllib.parse import urljoin


def sync_product(product):
    """Create/update a product remotely, or simulate sync if credentials are absent."""
    store_url = os.getenv("WC_STORE_URL", "").strip().rstrip("/")
    consumer_key = os.getenv("WC_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("WC_CONSUMER_SECRET", "").strip()

    if not (store_url and consumer_key and consumer_secret):
        return {
            "ok": True,
            "status": "Demo synced",
            "message": "Demo sync completed (no live WooCommerce credentials configured).",
            "mode": "demo",
        }

    try:
        import requests
        api_url = urljoin(store_url + "/", "wp-json/wc/v3/products")
        auth = (consumer_key, consumer_secret)
        params = {"sku": product["sku"]}
        lookup = requests.get(api_url, params=params, auth=auth, timeout=8)
        lookup.raise_for_status()
        matches = lookup.json()
        payload = {
            "name": product["name"],
            "type": "simple",
            "sku": product["sku"],
            "regular_price": f"{float(product['price']):.2f}",
            "description": product.get("description", ""),
            "manage_stock": True,
            "stock_quantity": int(product["stock"]),
            "categories": [],
        }
        if matches:
            remote_id = matches[0].get("id")
            response = requests.put(f"{api_url}/{remote_id}", json=payload, auth=auth, timeout=8)
            action = "updated"
        else:
            response = requests.post(api_url, json=payload, auth=auth, timeout=8)
            action = "created"
        response.raise_for_status()
        return {"ok": True, "status": "Synced", "message": f"Product {action} in live WooCommerce (SKU {product['sku']}).", "mode": "live"}
    except Exception as exc:
        # Return a concise message; do not log secrets or request headers.
        return {"ok": False, "status": "Failed", "message": f"Live sync failed: {type(exc).__name__}. Check store URL, API permissions, and connectivity.", "mode": "live"}
