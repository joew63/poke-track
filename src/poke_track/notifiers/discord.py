import os

import requests

from ..models import StockResult, StockStatus
from .base import Notifier


class DiscordNotifier(Notifier):
    def is_configured(self) -> bool:
        return bool(os.environ.get("DISCORD_WEBHOOK_URL"))

    def send(self, result: StockResult) -> None:
        webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        product = result.product
        if result.status == StockStatus.IN_STOCK:
            price_part = f" — {result.price}" if result.price else ""
            content = f"\U0001f7e2 **{product.name}** is in stock!{price_part}\n{product.url}"
        else:
            content = f"{product.name}: {result.status.value}\n{product.url}"

        resp = requests.post(webhook_url, json={"content": content}, timeout=10)
        resp.raise_for_status()
