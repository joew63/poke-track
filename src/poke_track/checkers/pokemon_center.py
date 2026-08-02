from typing import Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..models import Product, StockResult, StockStatus
from ._browser import rendered_page
from .base import Checker


def _classify(body_text: str, add_to_cart_disabled: Optional[bool]) -> tuple[StockStatus, str]:
    if "sold out" in body_text.lower() or "out of stock" in body_text.lower():
        return StockStatus.OUT_OF_STOCK, ""
    if add_to_cart_disabled is not None:
        status = StockStatus.OUT_OF_STOCK if add_to_cart_disabled else StockStatus.IN_STOCK
        return status, ""
    return (
        StockStatus.UNKNOWN,
        "could not find stock indicators (page layout may have changed, or request was blocked)",
    )


class PokemonCenterChecker(Checker):
    store_name = "pokemoncenter"

    def check(self, product: Product) -> StockResult:
        try:
            with rendered_page(product.url) as (response, page):
                if response and response.status >= 400:
                    return StockResult(
                        product,
                        StockStatus.UNKNOWN,
                        detail=f"HTTP {response.status} (likely blocked by bot protection)",
                    )
                body_text = page.inner_text("body")
                add_to_cart = page.query_selector('button:has-text("Add to Cart")')
                add_to_cart_disabled = (
                    add_to_cart.get_attribute("disabled") is not None if add_to_cart else None
                )
        except PlaywrightTimeoutError:
            return StockResult(product, StockStatus.UNKNOWN, detail="page load timed out (possibly blocked)")

        status, detail = _classify(body_text, add_to_cart_disabled)
        return StockResult(product, status, detail=detail)
