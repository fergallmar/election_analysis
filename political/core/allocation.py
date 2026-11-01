"""Interface and registry of seat allocation methods.

To add a new method (Sainte-Laguë, Hare, ...): subclass `AllocationMethod`,
decorate it with `@register_method("name")` and import its module somewhere
that is always loaded (see `political/election.py`). `Election` can then use it
by name or by class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class AllocationMethod(ABC):
    """Allocation of the seats of ONE district.

    Constructor contract: ``Method(seats, region="", warn=False, **options)``.
    """

    def __init__(self, seats: int, region: str = "", warn: bool = False,
                 **options: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def fit(self, votes: dict[str, float]) -> dict[str, int]:
        """Allocate seats. Returns party -> seats."""

    @abstractmethod
    def get_seats(self) -> dict[str, int]:
        """Seats per party (raises RuntimeError if not fitted)."""

    @abstractmethod
    def get_allocation(self) -> pd.DataFrame:
        """Seat-by-seat table (raises RuntimeError if not fitted)."""

    @abstractmethod
    def get_close_seats(self) -> pd.DataFrame:
        """Seats decided by a small margin (same columns as the allocation)."""


_REGISTRY: dict[str, type[AllocationMethod]] = {}


def register_method(name: str):
    """Class decorator that registers an allocation method under `name`."""

    def decorator(cls: type[AllocationMethod]) -> type[AllocationMethod]:
        _REGISTRY[name.lower()] = cls
        return cls

    return decorator


def get_method(method: str | type[AllocationMethod]) -> type[AllocationMethod]:
    """Resolve a registered name or an `AllocationMethod` subclass."""
    if isinstance(method, str):
        try:
            return _REGISTRY[method.lower()]
        except KeyError:
            raise KeyError(
                f"Unknown allocation method '{method}'. Available: {available_methods()}"
            ) from None
    if isinstance(method, type) and issubclass(method, AllocationMethod):
        return method
    raise TypeError("method must be a registered name or an AllocationMethod subclass")


def available_methods() -> list[str]:
    return sorted(_REGISTRY)
