"""Statistics attached to an `Election`.

A statistic receives the fitted election and an optional `scope` (the name of
any territory: a region, a province, ... or None for the whole entity), so the
same class works for a country and for any of its parts.

Future statistics (vote by age, sex, ...) subclass `Statistic`; the extra data
they need (surveys, census) goes in their own constructor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..election import Election


class Statistic(ABC):
    """Base class. `name` is the key used by `Election.get_statistic`."""

    name: str

    @abstractmethod
    def compute(self, election: Election, scope: str | None = None) -> pd.DataFrame:
        """Compute the statistic for the fitted `election` (optionally in `scope`)."""


class Gallagher(Statistic):
    """Gallagher disproportionality index between vote share and seat share."""

    name = "gallagher"

    def compute(self, election: Election, scope: str | None = None) -> pd.DataFrame:
        s = election.summary(scope=scope)
        diff = (s["vote_share"] - s["seat_share"]) * 100
        return pd.DataFrame({"gallagher": [float((0.5 * (diff**2).sum()) ** 0.5)]})
