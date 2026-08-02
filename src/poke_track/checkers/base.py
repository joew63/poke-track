from abc import ABC, abstractmethod

from ..models import Product, StockResult


class Checker(ABC):
    store_name: str

    @abstractmethod
    def check(self, product: Product) -> StockResult: ...
