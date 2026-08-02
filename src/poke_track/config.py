from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml
from dotenv import load_dotenv

from .checkers import REGISTRY
from .models import Product

DEFAULT_POLL_INTERVAL_SECONDS = 300

# Stores whose search/category pages are reliable enough to auto-discover products from.
# Target/Pokemon Center gate this behind the same bot detection as their product pages
# (often worse, since category pages are hit far more by bots than single product pages),
# so for now only Best Buy's official search API supports this.
SEARCHABLE_STORES = {"bestbuy"}


@dataclass
class SearchQuery:
    store: str
    search: str
    match_keywords: List[str] = field(default_factory=list)
    name: str = ""


@dataclass
class AppConfig:
    poll_interval_seconds: int
    products: List[Product]
    search_queries: List[SearchQuery]


def load_config(config_path: str = "config.yaml", env_path: Optional[str] = None) -> AppConfig:
    load_dotenv(env_path)

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Copy config.example.yaml to {config_path} "
            "and fill in the products you want to track."
        )

    raw = yaml.safe_load(path.read_text()) or {}
    poll_interval = int(raw.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))

    products = []
    search_queries = []
    for idx, item in enumerate(raw.get("products", [])):
        store = item.get("store")
        if store not in REGISTRY:
            raise ValueError(
                f"products[{idx}]: unknown store '{store}'. Supported stores: {', '.join(REGISTRY)}"
            )

        search = item.get("search")
        url = item.get("url")

        if search:
            if store not in SEARCHABLE_STORES:
                raise ValueError(
                    f"products[{idx}]: 'search' is only supported for {', '.join(SEARCHABLE_STORES)} "
                    f"(their search results are gated by bot detection for other stores) — "
                    f"use a specific 'url' for '{store}' instead."
                )
            search_queries.append(
                SearchQuery(
                    store=store,
                    search=search,
                    match_keywords=item.get("match_keywords") or [],
                    name=item.get("name", ""),
                )
            )
            continue

        if not url:
            raise ValueError(f"products[{idx}]: needs either 'url' or 'search'")
        name = item.get("name") or url
        products.append(Product(store=store, url=url, name=name))

    if not products and not search_queries:
        raise ValueError(f"No products configured in {path}")

    return AppConfig(poll_interval_seconds=poll_interval, products=products, search_queries=search_queries)
