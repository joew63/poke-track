from abc import ABC, abstractmethod

from ..models import StockResult


class Notifier(ABC):
    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def send(self, result: StockResult) -> None: ...
