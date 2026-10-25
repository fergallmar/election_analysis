"""Generic territorial structure shared by every country.

The country is a tree of `Territory` nodes (level 1 = region, level 2 =
province, level 3 = island, ...). Seats are stored on the node that is the
electoral district *for each chamber*, so different chambers can use different
levels, even within the same country (e.g. Spanish Senate: province on the
mainland, island in the Canary/Balearic Islands).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, NamedTuple


@dataclass(frozen=True, eq=False)
class Territory:
    """A node of the territorial tree.

    Parameters
    ----------
    name : territory name.
    children : sub-territories (next level down).
    seats : seats elected at THIS node, keyed by chamber
        (e.g. {"congress": 7, "senate": 4}). A node with seats for a chamber
        is an electoral district of that chamber; its children must not have
        seats for the same chamber.
    """

    name: str
    children: tuple[Territory, ...] = ()
    seats: dict[str, int] = field(default_factory=dict)


class District(NamedTuple):
    """Electoral district of a chamber."""

    name: str
    path: tuple[str, ...]  # e.g. ("Canarias", "Santa Cruz de Tenerife", "Tenerife")
    seats: int


@dataclass(frozen=True, eq=False)
class Country:
    """Country definition.

    Parameters
    ----------
    name : country name.
    level_names : label of each level, top-down, e.g.
        ("Autonomous Community", "Province", "Island").
    regions : level-1 territories.
    expected_seats : optional {chamber: total} used by `validate`.
    """

    name: str
    level_names: tuple[str, ...]
    regions: tuple[Territory, ...]
    expected_seats: dict[str, int] = field(default_factory=dict)

    def walk(self) -> Iterator[tuple[tuple[str, ...], Territory]]:
        """Yield (path, territory) for every node, depth first."""

        def _walk(node: Territory, path: tuple[str, ...]):
            path = path + (node.name,)
            yield path, node
            for child in node.children:
                yield from _walk(child, path)

        for region in self.regions:
            yield from _walk(region, ())

    def chambers(self) -> list[str]:
        return sorted({ch for _, t in self.walk() for ch in t.seats})

    def districts(self, chamber: str) -> list[District]:
        """Electoral districts of a chamber, in tree order."""
        return [District(t.name, path, t.seats[chamber])
                for path, t in self.walk() if chamber in t.seats]

    def get_district(self, chamber: str, name: str) -> District:
        found = [d for d in self.districts(chamber) if d.name == name]
        if not found:
            raise KeyError(f"No '{chamber}' district named '{name}'")
        return found[0]

    def seats(self, chamber: str) -> dict[str, int]:
        """Seats per district name for a chamber."""
        return {d.name: d.seats for d in self.districts(chamber)}

    def seats_by_region(self, chamber: str) -> dict[str, int]:
        """Seats per level-1 region for a chamber (aggregated)."""
        out = {r.name: 0 for r in self.regions}
        for d in self.districts(chamber):
            out[d.path[0]] += d.seats
        return out

    def total_seats(self, chamber: str) -> int:
        return sum(d.seats for d in self.districts(chamber))

    def validate(self) -> None:
        """Check structural consistency and expected totals."""
        for path, t in self.walk():
            for chamber in t.seats:
                for _, sub in self._descendants(t):
                    if chamber in sub.seats:
                        raise ValueError(
                            f"'{chamber}': '{'/'.join(path)}' and its descendant "
                            f"'{sub.name}' both have seats (double counting)")
        for chamber, expected in self.expected_seats.items():
            total = self.total_seats(chamber)
            if total != expected:
                raise ValueError(f"'{chamber}': {total} seats, expected {expected}")
        for chamber in self.chambers():
            names = [d.name for d in self.districts(chamber)]
            dupes = {n for n in names if names.count(n) > 1}
            if dupes:
                raise ValueError(f"'{chamber}': duplicated district names {dupes}")

    @staticmethod
    def _descendants(node: Territory) -> Iterator[tuple[int, Territory]]:
        for child in node.children:
            yield 1, child
            for depth, sub in Country._descendants(child):
                yield depth + 1, sub
