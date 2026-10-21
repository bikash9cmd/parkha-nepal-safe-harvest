"""The label book: official waiting periods and rates, and Nepal's banned list.

Two tables, kept apart on purpose:

- data/labels.csv: rows transcribed from India's CIB&RC "Major Uses of Pesticides" (most
  products sold in Nepal are Indian-made and carry these label claims). One row is one product
  on one crop for the listed pests, with its rate per hectare and its waiting period in days.
- data/nepal_banned.csv: what Nepal has banned and when.

An Indian label row does not make a product legal in Nepal. Carbofuran, carbosulfan and
chlorpyrifos all have label rows here and are all banned in Nepal; the ban list always wins
(bug #3 in docs/CHALLENGES_AND_BUGS.md).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import config


@dataclass(frozen=True)
class LabelRow:
    chemical: str
    product: str
    crop: str
    pests: tuple[str, ...]
    ai_g_per_ha: str
    product_per_ha: str
    unit: str
    waiting_days: int | None
    source: str

    def rate_per_ha(self) -> tuple[float, float] | None:
        """(low, high) product per hectare, or None when the label gives no usable rate or unit."""
        if not self.product_per_ha or not self.unit:
            return None
        parts = [float(p) for p in self.product_per_ha.split("-")]
        return parts[0], parts[-1]


@dataclass(frozen=True)
class Ban:
    chemical: str
    year: int
    note: str
    source: str


class LabelBook:
    def __init__(self, rows: list[LabelRow], bans: dict[str, Ban], sources: dict[str, dict]):
        self.rows = rows
        self.bans = bans
        self.sources = sources

    @classmethod
    def load(cls, data_dir: Path = config.DATA_DIR) -> LabelBook:
        rows = []
        with open(data_dir / "labels.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append(
                    LabelRow(
                        chemical=r["chemical"],
                        product=r["product"],
                        crop=r["crop"],
                        pests=tuple(p.strip() for p in r["pests"].split(";") if p.strip()),
                        ai_g_per_ha=r["ai_g_per_ha"],
                        product_per_ha=r["product_per_ha"],
                        unit=r["unit"],
                        # A blank waiting period is "not specified", never zero.
                        waiting_days=int(r["waiting_days"]) if r["waiting_days"].strip() else None,
                        source=r["source"],
                    )
                )
        bans = {}
        with open(data_dir / "nepal_banned.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                bans[r["chemical"]] = Ban(r["chemical"], int(r["banned_year"]), r["note"], r["source"])
        with open(data_dir / "sources.csv", encoding="utf-8") as f:
            sources = {r["id"]: r for r in csv.DictReader(f)}
        return cls(rows, bans, sources)

    def ban(self, chemical: str) -> Ban | None:
        return self.bans.get(chemical)

    def rows_for(self, chemical: str, crop: str | None = None) -> list[LabelRow]:
        return [r for r in self.rows if r.chemical == chemical and (crop is None or r.crop == crop)]

    def crop_waiting_days(self, chemical: str, crop: str) -> int | None:
        """The waiting period for a product on a crop: the longest across that crop's rows.

        A waiting period protects the person eating the crop, so it does not depend on the pest.
        When two rows disagree (neem on tomato: 3 days for one formulation, 5 for another) the
        longer one is used, because the farmer rarely knows which formulation they have.
        """
        days = [r.waiting_days for r in self.rows_for(chemical, crop)]
        if not days or any(d is None for d in days):
            return None
        return max(days)

    def options(self, crop: str, pest: str | None) -> list[LabelRow]:
        """Products a farmer could use: on a label for this crop and pest, with a waiting period, not banned.

        The pest must match. A label for "leaf miner" on tomato is for Liriomyza, not for Tuta
        absoluta; the lexicon keeps those apart so this match is exact.
        """
        out = []
        for r in self.rows:
            if r.crop != crop or self.ban(r.chemical) or r.waiting_days is None:
                continue
            if pest is not None and pest not in r.pests:
                continue
            out.append(r)
        return sorted(out, key=lambda r: (r.waiting_days, r.chemical))

    def source_title(self, source_ids: str) -> list[str]:
        return [self.sources[s]["title"] for s in source_ids.split(";") if s in self.sources]


def per_unit_area(rate_per_ha: tuple[float, float]) -> dict[str, tuple[float, float]]:
    """A per-hectare rate in the units farmers use: ropani in the hills, kattha in the Terai."""
    lo, hi = rate_per_ha

    def conv(m2: float) -> tuple[float, float]:
        f = m2 / config.HECTARE_M2
        return round(lo * f, 1), round(hi * f, 1)

    return {"ropani": conv(config.ROPANI_M2), "kattha": conv(config.KATTHA_M2)}


@lru_cache(maxsize=1)
def default_book() -> LabelBook:
    return LabelBook.load()
