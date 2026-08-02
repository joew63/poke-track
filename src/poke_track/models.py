from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Product:
    store: str
    url: str
    name: str

    @property
    def key(self) -> str:
        return f"{self.store}:{self.url}"


@dataclass
class StockResult:
    product: Product
    status: StockStatus
    price: Optional[str] = None
    detail: str = ""
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
