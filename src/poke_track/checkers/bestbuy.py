import os
import re
from typing import List, Optional
from urllib.parse import quote

import requests

from ..models import Product, StockResult, StockStatus
from .base import Checker

API_URL = "https://api.bestbuy.com/v1/products(sku={sku})"
SHOW_FIELDS = "sku,name,salePrice,onlineAvailability,inStoreAvailability"


def search_products(search_term: str, api_key: str) -> List[dict]:
    """Query Best Buy's official search API for products matching `search_term`.

    Best Buy's filter syntax needs each word as its own repeated search= clause
    joined by & *inside* the parentheses (not a single URL-encoded phrase), or a
    multi-word phrase gets interpreted as an OR of its words.
    """
    words = search_term.split()
    search_expr = "&".join(f"search={quote(word)}" for word in words)
    resp = requests.get(
        f"https://api.bestbuy.com/v1/products({search_expr})",
        params={"apiKey": api_key, "format": "json", "show": SHOW_FIELDS, "pageSize": 100},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("products", [])


def _extract_sku(url: str) -> str:
    if url.isdigit():
        return url
    match = re.search(r"/sku/(\d+)", url) or re.search(r"skuId=(\d+)", url)
    if match:
        return match.group(1)
    raise ValueError(
        f"Could not find a Best Buy SKU in url '{url}'. Use a URL that contains "
        "/sku/NNNNNNN (visible on the product page URL), or set 'url' to just the numeric SKU."
    )


def _classify(item: dict) -> tuple[StockStatus, Optional[str]]:
    in_stock = bool(item.get("onlineAvailability") or item.get("inStoreAvailability"))
    status = StockStatus.IN_STOCK if in_stock else StockStatus.OUT_OF_STOCK
    price = str(item["salePrice"]) if item.get("salePrice") is not None else None
    return status, price


class BestBuyChecker(Checker):
    store_name = "bestbuy"

    def check(self, product: Product) -> StockResult:
        api_key = os.environ.get("BESTBUY_API_KEY")
        if not api_key:
            return StockResult(product, StockStatus.UNKNOWN, detail="BESTBUY_API_KEY not set")

        try:
            sku = _extract_sku(product.url)
        except ValueError as e:
            return StockResult(product, StockStatus.UNKNOWN, detail=str(e))

        try:
            resp = requests.get(
                API_URL.format(sku=sku),
                params={"apiKey": api_key, "format": "json", "show": SHOW_FIELDS},
                timeout=15,
            )
        except requests.RequestException as e:
            return StockResult(product, StockStatus.UNKNOWN, detail=f"request failed: {e}")

        if resp.status_code != 200:
            return StockResult(product, StockStatus.UNKNOWN, detail=f"HTTP {resp.status_code} from Best Buy API")

        items = resp.json().get("products", [])
        if not items:
            return StockResult(product, StockStatus.UNKNOWN, detail=f"SKU {sku} not found")

        status, price = _classify(items[0])
        return StockResult(product, status, price=price)
