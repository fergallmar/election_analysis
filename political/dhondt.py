"""D'Hondt method for seat allocation."""

from __future__ import annotations

import math
import warnings

import pandas as pd


class DHondt:
    """D'Hondt seat allocation for a single region.

    Region parameters go in the constructor; the parties come with the votes
    in `fit`, since they change between elections (and the dict already links
    each party to its votes).

    Parameters
    ----------
    seats : number of seats to allocate.
    region : region name (informational).
    threshold : minimum share of total votes (0-1) to take part, e.g. 0.03.
    close_margin : a seat is flagged as "close" when the relative gap between
        the winning quotient and the runner-up quotient is <= this value
        (0.05 = 5%).
    warn : emit a `warnings.warn` when there are close seats.

    Attributes (set by `fit`)
    -------------------------
    seats_ : dict party -> seats.
    allocation_ : DataFrame, one row per seat in order of assignment.
    quotients_ : DataFrame, party x divisor quotients.
    excluded_ : parties left out by the threshold.

    Use the `get_*` methods to retrieve them; they raise `RuntimeError`
    if the model has not been fitted.
    """

    seats_: dict[str, int]
    allocation_: pd.DataFrame
    quotients_: pd.DataFrame
    excluded_: list[str]

    def __init__(
        self,
        seats: int,
        region: str = "",
        threshold: float = 0.0,
        close_margin: float = 0.05,
        warn: bool = True,
    ) -> None:
        if seats < 1:
            raise ValueError("seats must be >= 1")
        if not 0 <= threshold < 1:
            raise ValueError("threshold must be in [0, 1)")
        self.seats = seats
        self.region = region
        self.threshold = threshold
        self.close_margin = close_margin
        self.warn = warn

    def _check_fitted(self) -> None:
        if not hasattr(self, "seats_"):
            raise RuntimeError("DHondt has not been fitted yet; call fit() first.")

    def fit(self, votes: dict[str, int], blank_votes: int = 0) -> dict[str, int]:
        """Allocate seats and return the dict party -> seats.

        Parameters
        ----------
        votes : mapping party -> number of votes.
        blank_votes : blank votes, counted for the threshold only.
        """
        if not votes:
            raise ValueError("votes cannot be empty")
        total = sum(votes.values()) + blank_votes
        if total <= 0:
            raise ValueError("total votes must be > 0")

        eligible = {p: v for p, v in votes.items() if v > 0 and v / total >= self.threshold}
        excluded = [p for p in votes if p not in eligible]
        if not eligible:
            raise ValueError("no party reaches the threshold")

        won = {p: 0 for p in votes}
        rows = []
        for n in range(1, self.seats + 1):
            q = {p: v / (won[p] + 1) for p, v in eligible.items()}
            # Ties: more total votes first, then name (deterministic).
            order = sorted(q, key=lambda p: (-q[p], -eligible[p], p))
            winner = order[0]
            runner = order[1] if len(order) > 1 else None
            won[winner] += 1

            if runner is not None:
                margin = q[winner] - q[runner]
                margin_pct = margin / q[winner]
                # Votes the runner-up would need to take this seat.
                votes_to_flip = math.floor(q[winner] * (won[runner] + 1) - eligible[runner]) + 1
            else:
                margin = margin_pct = votes_to_flip = float("nan")

            rows.append(
                {
                    "seat": n,
                    "party": winner,
                    "party_seat_no": won[winner],
                    "quotient": q[winner],
                    "runner_up": runner,
                    "runner_up_quotient": q[runner] if runner else float("nan"),
                    "margin": margin,
                    "margin_pct": margin_pct,
                    "votes_to_flip": votes_to_flip,
                    "close": bool(runner is not None and margin_pct <= self.close_margin),
                }
            )

        allocation = pd.DataFrame(rows)
        quotients = pd.DataFrame(
            {p: [v / d for d in range(1, self.seats + 1)] for p, v in eligible.items()},
            index=pd.Index(range(1, self.seats + 1), name="divisor"),
        ).T
        self.seats_ = won
        self.allocation_ = allocation
        self.quotients_ = quotients
        self.excluded_ = excluded

        if self.warn and allocation["close"].any():
            close = allocation[allocation["close"]]
            detail = "; ".join(
                f"seat {r.seat}: {r.party} over {r.runner_up} "
                f"({r.margin_pct:.2%}, ~{r.votes_to_flip} votes)"
                for r in close.itertuples()
            )
            warnings.warn(f"[{self.region or 'region'}] close seats -> {detail}", stacklevel=2)
        return dict(won)

    def get_seats(self) -> dict[str, int]:
        """Seats per party."""
        self._check_fitted()
        return dict(self.seats_)

    def get_allocation(self) -> pd.DataFrame:
        """Seat-by-seat allocation table."""
        self._check_fitted()
        return self.allocation_.copy()

    def get_quotients(self) -> pd.DataFrame:
        """Party x divisor quotient table."""
        self._check_fitted()
        return self.quotients_.copy()

    def get_excluded(self) -> list[str]:
        """Parties below the threshold."""
        self._check_fitted()
        return list(self.excluded_)

    def get_close_seats(self) -> pd.DataFrame:
        """Seats whose margin against the runner-up is <= close_margin."""
        self._check_fitted()
        return pd.DataFrame(self.allocation_.loc[self.allocation_["close"]])

    def get_last_seat(self) -> pd.Series:
        """Row of the last allocated seat, the one most likely to change."""
        self._check_fitted()
        return self.allocation_.iloc[-1].copy()
