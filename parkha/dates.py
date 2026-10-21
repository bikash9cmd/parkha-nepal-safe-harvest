"""Spray dates in questions, and dates in answers, in AD and Bikram Sambat.

Farmers say when they sprayed the way they say anything else: "हिजो" (yesterday), "३ दिन अगाडि"
(three days ago), "asoj 28", "कात्तिक ३" or "2026-10-18". A spray date is always in the past, so a
BS date without a year is the most recent such day on or before today.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import nepali_datetime as nd

NE_DIGITS = "०१२३४५६७८९"
_TO_ASCII = str.maketrans(NE_DIGITS, "0123456789")
_TO_NE = str.maketrans("0123456789", NE_DIGITS)

BS_MONTHS_NE = ["बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज", "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"]
BS_MONTHS_EN = [
    "Baisakh",
    "Jestha",
    "Asar",
    "Saun",
    "Bhadau",
    "Asoj",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chaitra",
]
_BS_ALIASES = {
    1: ["बैशाख", "वैशाख", "बैसाख", "baisakh", "baishakh"],
    2: ["जेठ", "जेष्ठ", "jestha", "jeth"],
    3: ["असार", "आषाढ", "asar", "ashar", "asadh"],
    4: ["साउन", "श्रावण", "saun", "sawan", "shrawan"],
    5: ["भदौ", "भाद्र", "bhadau", "bhadra", "bhado"],
    6: ["असोज", "आश्विन", "asoj", "ashwin", "aswin", "ashoj"],
    7: ["कात्तिक", "कार्तिक", "kartik", "kattik"],
    8: ["मंसिर", "मङ्सिर", "mangsir", "mansir"],
    9: ["पुस", "पौष", "poush", "paush"],
    10: ["माघ", "magh"],
    11: ["फागुन", "फाल्गुन", "falgun", "fagun", "phagun"],
    12: ["चैत", "चैत्र", "chaitra", "chait"],
}
_AD_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip

_RELATIVE = [
    (re.compile(r"\b(today|aaja|aja)\b|आज", re.I), 0),
    (re.compile(r"\b(yesterday|hijo)\b|हिजो", re.I), 1),
    (re.compile(r"\b(day before yesterday|asti|aasti)\b|अस्ति", re.I), 2),
]
_DAYS_AGO = re.compile(r"(\d+)\s*(?:days?|din|दिन)\s*(?:ago|agadi|aghi|अगाडि|अघि|पहिले)", re.I)
_LAST_WEEK = re.compile(r"\b(last week|gaya hapta|gayeko hapta)\b|गएको हप्ता", re.I)
_ISO = re.compile(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b")
_AD_TEXT = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?(?:,?\s+(20\d\d))?\b|\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:,?\s+(20\d\d))?\b"
)


def ascii_digits(text: str) -> str:
    return text.translate(_TO_ASCII)


def ne_digits(value) -> str:
    return str(value).translate(_TO_NE)


def _bs_month(word: str) -> int | None:
    w = word.lower()
    for m, names in _BS_ALIASES.items():
        if any(w.startswith(n.lower()) for n in names):
            return m
    return None


def _bs_to_ad(year: int, month: int, day: int) -> date | None:
    try:
        return nd.date(year, month, day).to_datetime_date()
    except (ValueError, OverflowError):
        return None


def _bs_match(text: str, today: date) -> date | None:
    words = re.findall(r"[ऀ-ॿ]+|[A-Za-z]+|\d+", text)
    for i, w in enumerate(words):
        month = _bs_month(w)
        if month is None:
            continue
        # "असोज २८" or "२८ असोज", with an optional four-digit BS year on either side.
        nums = [int(x) for x in words[max(0, i - 2) : i + 3] if x.isdigit()]
        days = [n for n in nums if 1 <= n <= 32]
        years = [n for n in nums if 2000 <= n <= 2200]
        if not days:
            continue
        day = days[0]
        if years:
            return _bs_to_ad(years[0], month, day)
        this_year = nd.date.from_datetime_date(today).year
        for y in (this_year, this_year - 1):
            d = _bs_to_ad(y, month, day)
            if d and d <= today:
                return d
    return None


def parse_spray_date(text: str, today: date) -> date | None:
    """The date a spray happened, from a question. None when the question gives no date."""
    t = ascii_digits(text)
    m = _DAYS_AGO.search(t)
    if m:
        return today - timedelta(days=int(m.group(1)))
    m = _ISO.search(t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    bs = _bs_match(t, today)
    if bs:
        return bs
    for m in _AD_TEXT.finditer(t):
        day, mon, year = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(4), m.group(6))
        month = _AD_MONTHS.get(mon[:3].lower())
        if not month:
            continue
        y = int(year) if year else today.year
        try:
            d = date(y, month, int(day))
        except ValueError:
            continue
        if not year and d > today:
            d = date(y - 1, month, int(day))
        return d
    for pat, back in _RELATIVE:
        if pat.search(t):
            return today - timedelta(days=back)
    if _LAST_WEEK.search(t):
        return None  # too vague to count a waiting period from; the answer asks for the day
    return None


def bs(d: date) -> nd.date:
    return nd.date.from_datetime_date(d)


def fmt_en(d: date) -> str:
    b = bs(d)
    return f"{d.day} {d.strftime('%B')} {d.year} ({b.day} {BS_MONTHS_EN[b.month - 1]} {b.year} BS)"


def fmt_ne(d: date) -> str:
    b = bs(d)
    return f"{ne_digits(b.year)} {BS_MONTHS_NE[b.month - 1]} {ne_digits(b.day)} ({ne_digits(d.isoformat())})"
