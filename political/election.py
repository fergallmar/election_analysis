"""Election analysis over a territorial structure (country, region, ...)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import pandas as pd

from . import dhondt  # noqa: F401  (registers the "dhondt" method)
from .core.allocation import AllocationMethod, get_method
from .core.chambers import LOWER
from .core.stats import Statistic
from .core.structure import Country, Territory


@dataclass(frozen=True)
class Block:
    """Group of districts that share chamber and allocation method.

    Parameters
    ----------
    name : block identifier.
    chamber : chamber whose districts the block allocates (see core.chambers).
    method : registered method name or `AllocationMethod` subclass.
    method_kwargs : options passed to the method (e.g. {"threshold": 0.03}).
    districts : restrict the block to these district names (None = all the
        districts of the chamber). Blocks of the same chamber cannot overlap.
    """

    name: str
    chamber: str = LOWER
    method: str | type[AllocationMethod] = "dhondt"
    method_kwargs: dict[str, Any] = field(default_factory=dict)
    districts: tuple[str, ...] | None = None


@dataclass
class _Run:
    path: tuple[str, ...]
    votes: dict[str, float]
    method: AllocationMethod


class Election:
    """Runs the allocation of every district of a structure and analyses it.

    Parameters
    ----------
    structure : `Country` or `Territory` (e.g. a single region).
    method, chamber, method_kwargs : shortcut for a single block.
    blocks : explicit list of `Block` (overrides the shortcut).

    Votes are given at the most detailed level you have (e.g. provinces); the
    votes of a district that is not in the table are the sum of its
    descendants. That is what makes `simulate` possible (other districting).
    """

    def __init__(
        self,
        structure: Country | Territory,
        method: str | type[AllocationMethod] = "dhondt",
        chamber: str = LOWER,
        method_kwargs: dict[str, Any] | None = None,
        blocks: list[Block] | None = None,
    ) -> None:
        if isinstance(structure, Territory):
            structure = Country.from_territory(structure)
        self.structure = structure
        self.blocks = list(blocks) if blocks else [
            Block("main", chamber, method, dict(method_kwargs or {}))]
        self.statistics: dict[str, Statistic] = {}
        self._tables: dict[str, pd.DataFrame] = {}
        self._results: dict[str, dict[str, _Run]] = {}
        self._check_blocks()

    # ------------------------------------------------------------------ setup
    def _check_blocks(self) -> None:
        names = [b.name for b in self.blocks]
        if len(set(names)) != len(names):
            raise ValueError("block names must be unique")
        used: dict[tuple[str, str], str] = {}
        for b in self.blocks:
            get_method(b.method)
            nodes = self._block_nodes(b)
            if not nodes:
                raise ValueError(f"Block '{b.name}': no districts for chamber '{b.chamber}'")
            for _, node in nodes:
                key = (b.chamber, node.name)
                if key in used:
                    raise ValueError(
                        f"District '{node.name}' in blocks '{used[key]}' and '{b.name}'")
                used[key] = b.name

    def _block_nodes(self, block: Block) -> list[tuple[tuple[str, ...], Territory]]:
        nodes = self.structure.district_nodes(block.chamber)
        if block.districts is not None:
            wanted = set(block.districts)
            unknown = wanted - {n.name for _, n in nodes}
            if unknown:
                raise KeyError(f"Block '{block.name}': unknown districts {sorted(unknown)}")
            nodes = [(p, n) for p, n in nodes if n.name in wanted]
        return nodes

    def add_statistic(self, statistic: Statistic) -> Election:
        self.statistics[statistic.name] = statistic
        return self

    # -------------------------------------------------------------------- fit
    @staticmethod
    def _as_frame(votes: Any) -> pd.DataFrame:
        if isinstance(votes, pd.DataFrame):
            frame = votes.copy()
        else:
            frame = pd.DataFrame.from_dict(votes, orient="index")
        if not frame.index.is_unique:
            raise ValueError("votes: duplicated territory names in the index")
        return frame.fillna(0)

    @classmethod
    def _votes_for(cls, node: Territory, table: pd.DataFrame) -> pd.Series:
        if node.name in table.index:
            return pd.Series(table.loc[node.name])
        if not node.children:
            raise KeyError(f"No votes for '{node.name}'")
        total = pd.Series(dtype=float)
        for child in node.children:
            total = total.add(cls._votes_for(child, table), fill_value=0)
        return total

    def fit(self, votes: Any, per_block: bool = False) -> dict:
        """Allocate the seats of every district.

        Parameters
        ----------
        votes : DataFrame (index = territory name, columns = party) or
            {territory: {party: votes}}.
        per_block : if True, `votes` is {block name: table}.

        Returns party -> seats when all blocks share a chamber, otherwise
        {block name: party -> seats}.
        """
        if per_block:
            missing = {b.name for b in self.blocks} - set(votes)
            if missing:
                raise KeyError(f"No votes for blocks {sorted(missing)}")
            tables = {b.name: self._as_frame(votes[b.name]) for b in self.blocks}
        else:
            table = self._as_frame(votes)
            tables = {b.name: table for b in self.blocks}

        results: dict[str, dict[str, _Run]] = {}
        for b in self.blocks:
            cls = get_method(b.method)
            kwargs = {"warn": False, **b.method_kwargs}
            runs = {}
            for path, node in self._block_nodes(b):
                v = self._votes_for(node, tables[b.name]).to_dict()
                alloc = cls(seats=node.seats[b.chamber], region=node.name, **kwargs)
                alloc.fit(v)
                runs[node.name] = _Run(path, v, alloc)
            results[b.name] = runs
        self._tables, self._results = tables, results

        if len({b.chamber for b in self.blocks}) == 1:
            return self.get_seats()
        return {b.name: self.get_seats(block=b.name) for b in self.blocks}

    # ---------------------------------------------------------------- helpers
    def _check_fitted(self) -> None:
        if not self._results:
            raise RuntimeError("Election has not been fitted yet; call fit() first.")

    def _select_blocks(self, block: str | None) -> list[Block]:
        if block is not None:
            found = [b for b in self.blocks if b.name == block]
            if not found:
                raise KeyError(f"Unknown block '{block}'")
            return found
        if len({b.chamber for b in self.blocks}) > 1:
            raise ValueError("Several chambers: specify `block`")
        return self.blocks

    def _single_block(self, block: str | None) -> Block:
        if block is None and len(self.blocks) > 1:
            raise ValueError("Several blocks: specify `block`")
        return self._select_blocks(block)[0]

    def _runs(self, block: str | None, scope: str | None) -> list[tuple[str, str, _Run]]:
        self._check_fitted()
        out = [(b.name, d, r) for b in self._select_blocks(block)
               for d, r in self._results[b.name].items()
               if scope is None or scope in r.path]
        if not out:
            raise KeyError(f"No districts found for scope '{scope}'")
        return out

    @staticmethod
    def _index(runs: list[tuple[str, str, _Run]]) -> pd.Index:
        if len({b for b, _, _ in runs}) == 1:
            return pd.Index([d for _, d, _ in runs], name="district")
        return pd.MultiIndex.from_tuples([(b, d) for b, d, _ in runs],
                                         names=["block", "district"])

    def districts_in(self, scope: str | None = None, block: str | None = None) -> list[str]:
        """Names of the districts inside `scope` (None = all)."""
        return [d for _, d, _ in self._runs(block, scope)]

    def get_district(self, name: str, block: str | None = None) -> AllocationMethod:
        """Allocation object of one district (all its get_* methods)."""
        for _, d, r in self._runs(block, None):
            if d == name:
                return r.method
        raise KeyError(f"Unknown district '{name}'")

    # ------------------------------------------------------ aggregated results
    def get_seats(self, block: str | None = None, scope: str | None = None) -> dict[str, int]:
        """Total seats per party."""
        s = self.get_seats_by_district(block, scope).sum().sort_values(ascending=False)
        return {p: int(v) for p, v in s.items()}

    def get_seats_by_district(self, block: str | None = None,
                              scope: str | None = None) -> pd.DataFrame:
        """District x party seats."""
        runs = self._runs(block, scope)
        df = pd.DataFrame([r.method.get_seats() for _, _, r in runs], index=self._index(runs))
        return df.fillna(0).astype(int)

    def get_votes_by_district(self, block: str | None = None,
                              scope: str | None = None) -> pd.DataFrame:
        """District x party votes (already aggregated to the district)."""
        runs = self._runs(block, scope)
        df = pd.DataFrame([r.votes for _, _, r in runs], index=self._index(runs))
        return df.fillna(0)

    def get_vote_share_by_district(self, block: str | None = None,
                                   scope: str | None = None) -> pd.DataFrame:
        v = self.get_votes_by_district(block, scope)
        return v.div(v.sum(axis=1), axis=0)

    def _group_level(self, df: pd.DataFrame, block, scope, level: int) -> pd.DataFrame:
        runs = self._runs(block, scope)
        keys = pd.Index([r.path[min(level, len(r.path)) - 1] for _, _, r in runs],
                        name=f"level_{level}")
        return df.groupby(keys, sort=False).sum()

    def get_seats_by_region(self, block: str | None = None, scope: str | None = None,
                            level: int = 1) -> pd.DataFrame:
        """Region (level 1 by default) x party seats."""
        return self._group_level(self.get_seats_by_district(block, scope), block, scope, level)

    def get_votes_by_region(self, block: str | None = None, scope: str | None = None,
                            level: int = 1) -> pd.DataFrame:
        return self._group_level(self.get_votes_by_district(block, scope), block, scope, level)

    def get_winners(self, by: str = "votes", block: str | None = None,
                    scope: str | None = None) -> pd.Series:
        """Winning party per district, by 'votes' or by 'seats'."""
        if by not in ("votes", "seats"):
            raise ValueError("by must be 'votes' or 'seats'")
        table = (self.get_votes_by_district(block, scope) if by == "votes"
                 else self.get_seats_by_district(block, scope))
        return table.idxmax(axis=1).rename("winner")

    def summary(self, block: str | None = None, scope: str | None = None) -> pd.DataFrame:
        """Votes, vote share, seats, seat share and gap per party."""
        votes = self.get_votes_by_district(block, scope).sum()
        seats = self.get_seats_by_district(block, scope).sum()
        df = pd.DataFrame({"votes": votes, "seats": seats}).fillna(0)
        df["seats"] = df["seats"].astype(int)
        df["vote_share"] = df["votes"] / df["votes"].sum()
        df["seat_share"] = df["seats"] / df["seats"].sum()
        df["seat_vote_gap"] = df["seat_share"] - df["vote_share"]
        df = df.sort_values(["seats", "votes"], ascending=False)
        return df[["votes", "vote_share", "seats", "seat_share", "seat_vote_gap"]]

    # ------------------------------------------------- per-district / margins
    def _concat(self, getter: str, block, scope) -> pd.DataFrame:
        frames = []
        for _, d, r in self._runs(block, scope):
            df = getattr(r.method, getter)().copy()
            df.insert(0, "district", d)
            df.insert(0, "region", r.path[0])
            frames.append(df)
        return pd.concat(frames, ignore_index=True)

    def get_allocation(self, district: str | None = None, block: str | None = None,
                       scope: str | None = None) -> pd.DataFrame:
        """Seat-by-seat table of one district, or of all (with region/district columns)."""
        if district is not None:
            return self.get_district(district, block).get_allocation()
        return self._concat("get_allocation", block, scope)

    def get_close_seats(self, block: str | None = None,
                        scope: str | None = None) -> pd.DataFrame:
        """Close seats of every district, tightest margin first."""
        df = self._concat("get_close_seats", block, scope)
        return df.sort_values("margin_pct").reset_index(drop=True)

    # ------------------------------------------------------------- statistics
    def get_statistic(self, name: str, scope: str | None = None) -> pd.DataFrame:
        self._check_fitted()
        if name not in self.statistics:
            raise KeyError(f"Unknown statistic '{name}'. Added: {sorted(self.statistics)}")
        return self.statistics[name].compute(self, scope)

    # ------------------------------------------------------------- simulation
    def simulate(
        self,
        block: str | None = None,
        level: int | None = None,
        seats: Mapping[str, int] | None = None,
        method: str | type[AllocationMethod] | None = None,
        method_kwargs: dict[str, Any] | None = None,
        refit: bool = True,
    ) -> Election:
        """New election with another districting and/or allocation method.

        Parameters
        ----------
        block : block to modify (optional if there is only one).
        level : move the districts of the block's chamber to this level
            (1 = region, 2 = province, ...); seats are added up.
        seats : override the seats of the new districts {name: seats}
            (requires `level`).
        method, method_kwargs : replace the allocation method / its options.
        refit : fit the new election with the same votes.

        Compare with `base.compare(alt)`.
        """
        target = self._single_block(block)
        if seats is not None and level is None:
            raise ValueError("`seats` requires `level`")
        redistrict = level is not None
        structure = self.structure
        if redistrict:
            if sum(b.chamber == target.chamber for b in self.blocks) > 1:
                raise NotImplementedError("Districting simulation needs one block per chamber")
            structure = structure.redistrict(target.chamber, level, seats)
        blocks = [
            replace(
                b,
                method=method if method is not None else b.method,
                method_kwargs=(dict(method_kwargs) if method_kwargs is not None
                               else b.method_kwargs),
                districts=None if redistrict else b.districts,
            ) if b is target else b
            for b in self.blocks
        ]
        new = Election(structure, blocks=blocks)
        new.statistics = dict(self.statistics)
        if refit and self._tables:
            new.fit(self._tables, per_block=True)
        return new

    def compare(self, other: Election, block: str | None = None,
                other_block: str | None = None) -> pd.DataFrame:
        """Total seats per party: this election (base) vs `other` (alt)."""
        base = pd.Series(self.get_seats(block))
        alt = pd.Series(other.get_seats(other_block if other_block is not None else block))
        df = pd.DataFrame({"base": base, "alt": alt}).fillna(0).astype(int)
        df["diff"] = df["alt"] - df["base"]
        return df.sort_values("base", ascending=False)

    # -------------------------------------------------------------------- map
    def get_map_table(self, by: str = "votes", block: str | None = None,
                      scope: str | None = None) -> pd.DataFrame:
        """District table (winner + seats per party) ready to join with geodata."""
        table = self.get_seats_by_district(block, scope)
        table.insert(0, "winner", self.get_winners(by, block, scope))
        return table.reset_index()

    def plot_map(self, geodata: Any, on: str = "district", geo_key: str = "name",
                 by: str = "votes", colors: Mapping[str, str] | None = None,
                 block: str | None = None, scope: str | None = None,
                 ax: Any = None, title: str | None = None, **plot_kwargs: Any) -> Any:
        """Map of the winner of each district.

        Parameters
        ----------
        geodata : GeoDataFrame or path to a file readable by geopandas. Its
            geometries must be at the same level as the block's districts
            (provinces, islands, ...).
        geo_key : column of `geodata` with the district name (exact match).
        by : colour by winner in 'votes' or in 'seats'.
        colors : {party: colour}; defaults to a categorical palette.
        Requires geopandas and matplotlib.
        """
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch

        if hasattr(geodata, "geometry"):
            gdf = geodata
        else:
            import geopandas as gpd

            gdf = gpd.read_file(geodata)
        table = self.get_map_table(by, block, scope)
        merged = gdf.merge(table, left_on=geo_key, right_on=on, how="left")
        missing = merged.loc[merged["winner"].isna(), geo_key].tolist()
        if missing:
            print(f"Warning: no results for geodata units: {missing}")

        parties = sorted(merged["winner"].dropna().unique())
        cmap = plt.get_cmap("tab10")
        palette = {p: (colors or {}).get(p, cmap(i % 10)) for i, p in enumerate(parties)}
        merged["_color"] = merged["winner"].map(palette).fillna("lightgrey")

        if ax is None:
            _, ax = plt.subplots(figsize=(8, 8))
        merged.plot(ax=ax, color=merged["_color"], edgecolor="white", linewidth=0.5,
                    **plot_kwargs)
        ax.legend(handles=[Patch(color=c, label=p) for p, c in palette.items()],
                  loc="lower left", frameon=False)
        ax.set_axis_off()
        if title:
            ax.set_title(title)
        return ax
