import argparse
import logging
import os
import random
import time

from dotenv import load_dotenv

from .checkers import REGISTRY
from .config import AppConfig, load_config
from .discovery import discover_products
from .models import Product, StockResult, StockStatus
from .notifiers import DiscordNotifier, EmailNotifier
from .notifiers.base import Notifier
from .state import StateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("poke_track")


def build_notifiers() -> list[Notifier]:
    candidates: list[Notifier] = [DiscordNotifier(), EmailNotifier()]
    configured = [n for n in candidates if n.is_configured()]
    if not configured:
        log.warning(
            "No notifiers configured — set DISCORD_WEBHOOK_URL and/or SMTP_* + EMAIL_TO in .env"
        )
    return configured


def gather_products(config: AppConfig) -> list[Product]:
    products = list(config.products)
    if config.search_queries:
        discovered = discover_products(config.search_queries, os.environ.get("BESTBUY_API_KEY"))
        products.extend(discovered)
    return products


def run_once(config: AppConfig, state: StateStore, notifiers: list[Notifier]) -> None:
    for product in gather_products(config):
        checker = REGISTRY[product.store]()
        try:
            result = checker.check(product)
        except Exception:
            log.exception(f"[{product.store}] {product.name}: checker crashed")
            time.sleep(random.uniform(1, 3))
            continue

        suffix = f" ({result.detail})" if result.detail else ""
        log.info(f"[{product.store}] {product.name}: {result.status.value}{suffix}")

        if state.record_and_should_notify(product.key, result.status):
            log.info(f"Notifying: {product.name} is in stock!")
            for notifier in notifiers:
                try:
                    notifier.send(result)
                except Exception:
                    log.exception(f"{notifier.__class__.__name__} failed to send")

        time.sleep(random.uniform(1, 3))

    state.save()


def send_test_notification(notifiers: list[Notifier]) -> None:
    product = Product(store="test", url="https://example.com", name="Test Product")
    result = StockResult(
        product=product, status=StockStatus.IN_STOCK, detail="this is a test notification from poke-track"
    )
    for notifier in notifiers:
        notifier.send(result)
        log.info(f"Sent test notification via {notifier.__class__.__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokemon card retail stock checker")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--state", default="state.json")
    parser.add_argument("--once", action="store_true", help="Run a single check pass and exit")
    parser.add_argument(
        "--test-notify", action="store_true", help="Send a test notification and exit"
    )
    parser.add_argument(
        "--renotify-after-hours",
        type=float,
        default=None,
        help="Re-send a notification if an item is still in stock this many hours after the last one",
    )
    args = parser.parse_args()

    load_dotenv()
    notifiers = build_notifiers()

    if args.test_notify:
        if not notifiers:
            raise SystemExit("No notifiers configured; set the relevant env vars first (see .env.example)")
        send_test_notification(notifiers)
        return

    config = load_config(args.config)
    renotify_seconds = (
        int(args.renotify_after_hours * 3600) if args.renotify_after_hours is not None else None
    )
    state = StateStore(args.state, renotify_after_seconds=renotify_seconds)

    if args.once:
        run_once(config, state, notifiers)
        return

    search_note = f" + {len(config.search_queries)} search quer{'y' if len(config.search_queries) == 1 else 'ies'}" if config.search_queries else ""
    log.info(
        f"Starting poke-track: {len(config.products)} product(s){search_note}, "
        f"polling every {config.poll_interval_seconds}s"
    )
    while True:
        run_once(config, state, notifiers)
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    main()
