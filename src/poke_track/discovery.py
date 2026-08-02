import logging
from typing import List, Optional

from .checkers.bestbuy import search_products
from .config import SearchQuery
from .models import Product

log = logging.getLogger("poke_track")


def _matches(name: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    lowered = name.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def discover_products(queries: List[SearchQuery], bestbuy_api_key: Optional[str]) -> List[Product]:
    discovered: List[Product] = []

    for query in queries:
        if query.store != "bestbuy":
            continue  # config.py already rejects other stores; guards future stores too
        if not bestbuy_api_key:
            log.warning(f"Skipping search '{query.search}': BESTBUY_API_KEY not set")
            continue

        try:
            items = search_products(query.search, bestbuy_api_key)
        except Exception:
            log.exception(f"Best Buy search failed for '{query.search}'")
            continue

        matched = [item for item in items if _matches(item.get("name", ""), query.match_keywords)]
        log.info(f"Best Buy search '{query.search}': {len(items)} result(s), {len(matched)} matched keywords")

        for item in matched:
            sku = item.get("sku")
            if sku is None:
                continue
            label = item.get("name", str(sku))
            name = f"{query.name}: {label}" if query.name else label
            discovered.append(Product(store="bestbuy", url=str(sku), name=name))

    return discovered
