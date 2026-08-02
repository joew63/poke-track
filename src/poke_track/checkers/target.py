from typing import Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..models import Product, StockResult, StockStatus
from ._browser import rendered_page
from .base import Checker


def _classify(shipping_text: Optional[str], section_text: Optional[str]) -> tuple[StockStatus, str]:
    # Target shows a focused "Shipping" cell when checking overall online availability;
    # per-store pickup text (e.g. "Out of stock at <store>") doesn't mean shipping is out.
    if shipping_text:
        t = shipping_text.lower()
        if "arrives by" in t:
            return StockStatus.IN_STOCK, shipping_text.strip()
        if "not available" in t or "unavailable" in t:
            return StockStatus.OUT_OF_STOCK, shipping_text.strip()

    if section_text:
        t = section_text.lower()
        if "arrives by" in t or "ready within" in t:
            return StockStatus.IN_STOCK, section_text.strip()
        if "out of stock" in t:
            return StockStatus.OUT_OF_STOCK, section_text.strip()

    return StockStatus.UNKNOWN, "could not find fulfillment section (page layout may have changed)"


class TargetChecker(Checker):
    store_name = "target"

    def check(self, product: Product) -> StockResult:
        try:
            with rendered_page(product.url) as (response, page):
                if response and response.status >= 400:
                    return StockResult(
                        product, StockStatus.UNKNOWN, detail=f"HTTP {response.status} (likely blocked)"
                    )
                shipping_el = page.query_selector('[data-test="fulfillment-cell-shipping"]')
                section_el = page.query_selector('[data-test="@web/AddToCart/FulfillmentSection"]')
                shipping_text = shipping_el.inner_text() if shipping_el else None
                section_text = section_el.inner_text() if section_el else None
        except PlaywrightTimeoutError:
            return StockResult(product, StockStatus.UNKNOWN, detail="page load timed out (possibly blocked)")

        status, detail = _classify(shipping_text, section_text)
        return StockResult(product, status, detail=detail)
