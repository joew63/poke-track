import json
from pathlib import Path

import pytest

from poke_track.checkers.bestbuy import _classify as bestbuy_classify
from poke_track.checkers.bestbuy import _extract_sku, search_products
from poke_track.checkers.pokemon_center import _classify as pc_classify
from poke_track.checkers.target import _classify as target_classify
from poke_track.models import StockStatus

FIXTURES = Path(__file__).parent / "fixtures"


# --- Best Buy -----------------------------------------------------------------------------


def test_extract_sku_from_sku_path():
    url = "https://www.bestbuy.com/product/.../JJG2TL34TS/sku/12717684"
    assert _extract_sku(url) == "12717684"


def test_extract_sku_from_bare_digits():
    assert _extract_sku("12717684") == "12717684"


def test_extract_sku_missing_raises():
    with pytest.raises(ValueError, match="Could not find a Best Buy SKU"):
        _extract_sku("https://www.bestbuy.com/product/foo/J3YSYH3WSP")


def test_search_products_builds_multi_word_query(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"products": [{"sku": 1, "name": "Pokemon Trading Card Game: Something"}]}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr("poke_track.checkers.bestbuy.requests.get", fake_get)

    results = search_products("Pokemon Trading Card Game", api_key="fake-key")

    # each word of a multi-word search needs its own repeated search= clause per
    # Best Buy's documented syntax, or it gets treated as an OR of the words
    assert captured["url"] == (
        "https://api.bestbuy.com/v1/products(search=Pokemon&search=Trading&search=Card&search=Game)"
    )
    assert captured["params"]["apiKey"] == "fake-key"
    assert len(results) == 1


def test_bestbuy_classify_in_stock_and_out_of_stock():
    samples = json.loads((FIXTURES / "bestbuy_sample.json").read_text())

    status, price = bestbuy_classify(samples["in_stock"])
    assert status == StockStatus.IN_STOCK
    assert price == "161.99"

    status, _ = bestbuy_classify(samples["out_of_stock"])
    assert status == StockStatus.OUT_OF_STOCK


# --- Target (captured from real product pages via headless browser during development) ----


def test_target_classify_out_of_stock_from_fulfillment_section():
    # captured verbatim from a real out-of-stock Target Pokemon TCG listing
    section_text = "Out of stock\nAdd to cart"
    status, _ = target_classify(shipping_text=None, section_text=section_text)
    assert status == StockStatus.OUT_OF_STOCK


def test_target_classify_in_stock_from_shipping_cell():
    # captured verbatim from a real in-stock Target listing's shipping cell
    shipping_text = "Shipping\nArrives by Wed, Aug 5"
    status, _ = target_classify(shipping_text=shipping_text, section_text=None)
    assert status == StockStatus.IN_STOCK


def test_target_classify_shipping_unavailable():
    shipping_text = "Shipping\nNot available"
    status, _ = target_classify(shipping_text=shipping_text, section_text=None)
    assert status == StockStatus.OUT_OF_STOCK


def test_target_classify_out_of_stock_pickup_does_not_shadow_available_shipping():
    # Target shows per-store pickup status ("Out of stock at <store>") separately from
    # shipping - the shipping cell should win when present.
    shipping_text = "Shipping\nArrives by Wed, Aug 5"
    section_text = "Pickup\nOut of stock at Northgate\nShipping\nArrives by Wed, Aug 5"
    status, _ = target_classify(shipping_text=shipping_text, section_text=section_text)
    assert status == StockStatus.IN_STOCK


def test_target_classify_unknown_when_no_selectors_found():
    status, detail = target_classify(shipping_text=None, section_text=None)
    assert status == StockStatus.UNKNOWN
    assert "layout may have changed" in detail


# --- Pokemon Center -------------------------------------------------------------------------


def test_pokemon_center_classify_sold_out_text():
    status, _ = pc_classify(body_text="This item is currently Sold Out.", add_to_cart_disabled=None)
    assert status == StockStatus.OUT_OF_STOCK


def test_pokemon_center_classify_add_to_cart_enabled():
    status, _ = pc_classify(body_text="Pokemon TCG Booster Bundle", add_to_cart_disabled=False)
    assert status == StockStatus.IN_STOCK


def test_pokemon_center_classify_add_to_cart_disabled():
    status, _ = pc_classify(body_text="Pokemon TCG Booster Bundle", add_to_cart_disabled=True)
    assert status == StockStatus.OUT_OF_STOCK


def test_pokemon_center_classify_unknown_when_blocked():
    status, detail = pc_classify(body_text="Access Denied", add_to_cart_disabled=None)
    assert status == StockStatus.UNKNOWN
    assert "blocked" in detail
