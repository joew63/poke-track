from poke_track.config import SearchQuery
from poke_track.discovery import discover_products

SAMPLE_RESULTS = [
    {"sku": 111, "name": "Pokemon Trading Card Game: Mega Evolution Elite Trainer Box"},
    {"sku": 222, "name": "Pokemon Trading Card Game: Mega Evolution Booster Bundle"},
    {"sku": 333, "name": "Pokemon Plush - Charmander"},
]


def test_discover_filters_by_match_keywords(monkeypatch):
    monkeypatch.setattr(
        "poke_track.discovery.search_products", lambda term, key: SAMPLE_RESULTS
    )
    query = SearchQuery(
        store="bestbuy",
        search="pokemon",
        match_keywords=["Elite Trainer Box", "Booster Bundle"],
        name="Best Buy Pokemon TCG",
    )
    products = discover_products([query], bestbuy_api_key="fake-key")

    skus = {p.url for p in products}
    assert skus == {"111", "222"}
    assert all(p.name.startswith("Best Buy Pokemon TCG: ") for p in products)


def test_discover_without_keywords_returns_everything(monkeypatch):
    monkeypatch.setattr(
        "poke_track.discovery.search_products", lambda term, key: SAMPLE_RESULTS
    )
    query = SearchQuery(store="bestbuy", search="pokemon", match_keywords=[], name="")
    products = discover_products([query], bestbuy_api_key="fake-key")
    assert len(products) == 3


def test_discover_skips_when_no_api_key():
    query = SearchQuery(store="bestbuy", search="pokemon", match_keywords=[], name="")
    products = discover_products([query], bestbuy_api_key=None)
    assert products == []


def test_discover_handles_search_failure_gracefully(monkeypatch):
    def raise_error(term, key):
        raise RuntimeError("boom")

    monkeypatch.setattr("poke_track.discovery.search_products", raise_error)
    query = SearchQuery(store="bestbuy", search="pokemon", match_keywords=[], name="")
    products = discover_products([query], bestbuy_api_key="fake-key")
    assert products == []
