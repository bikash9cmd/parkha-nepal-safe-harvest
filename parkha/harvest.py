"""The earliest safe harvest date: the one number in Parkha that a model never writes on its own.

earliest harvest = last spray + label waiting period (for that product on that crop).

There is deliberately no "about", no rounding and no "it's probably fine after a wash". Washing
does not remove systemic insecticides, and the RBPR test at Kalimati does not care how fresh the
produce looks.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import dates
from .labels import LabelBook


def safe_harvest(book: LabelBook, chemical: str, crop: str, spray_date: date, today: date) -> dict:
    ban = book.ban(chemical)
    days = book.crop_waiting_days(chemical, crop)
    result: dict = {
        "chemical": chemical,
        "crop": crop,
        "spray_date": spray_date.isoformat(),
        "banned_in_nepal": bool(ban),
        "banned_year": ban.year if ban else None,
        "waiting_days": days,
    }
    if days is None:
        result["status"] = "no_verified_waiting_period"
        return result
    earliest = spray_date + timedelta(days=days)
    result.update(
        earliest_harvest=earliest.isoformat(),
        earliest_harvest_en=dates.fmt_en(earliest),
        earliest_harvest_ne=dates.fmt_ne(earliest),
        days_left=max(0, (earliest - today).days),
        status="wait" if earliest > today else "ok_to_harvest",
    )
    return result
