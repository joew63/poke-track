import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import StockStatus


class StateStore:
    """Tracks each product's last known status so we only notify on OOS -> in-stock transitions."""

    def __init__(self, path: str = "state.json", renotify_after_seconds: Optional[int] = None):
        self.path = Path(path)
        self.renotify_after_seconds = renotify_after_seconds
        self._data: dict = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))

    def record_and_should_notify(self, product_key: str, status: StockStatus) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        prev = self._data.get(product_key)
        prev_status = prev.get("status") if prev else None

        # A failed/blocked check shouldn't erase the last known real status.
        effective_status = prev_status if status == StockStatus.UNKNOWN else status.value

        should_notify = False
        if status == StockStatus.IN_STOCK:
            if prev_status != StockStatus.IN_STOCK.value:
                should_notify = True
            elif self.renotify_after_seconds is not None and prev and prev.get("last_notified"):
                last_notified = datetime.fromisoformat(prev["last_notified"])
                elapsed = (datetime.now(timezone.utc) - last_notified).total_seconds()
                should_notify = elapsed >= self.renotify_after_seconds

        self._data[product_key] = {
            "status": effective_status,
            "last_check_result": status.value,
            "last_checked": now,
            "last_notified": now if should_notify else (prev.get("last_notified") if prev else None),
        }
        return should_notify
