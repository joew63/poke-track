from .base import Checker
from .bestbuy import BestBuyChecker
from .pokemon_center import PokemonCenterChecker
from .target import TargetChecker

REGISTRY: dict[str, type[Checker]] = {
    "bestbuy": BestBuyChecker,
    "target": TargetChecker,
    "pokemoncenter": PokemonCenterChecker,
}

__all__ = ["Checker", "REGISTRY"]
