"""The four read-only tools the model can call, and their Bedrock tool specs.

The model never sees the label table directly. It asks for options for a crop and pest, for a
product's status, or for a harvest date, and gets back a small dict. Every number the gate
allows in an answer (waiting days, dates, rates) comes from one of these dicts.

Arguments go through the lexicon first, so "गोलभेडा", "golbheda" and "tomato" are the same crop,
and unknown keys are dropped: a tool call cannot carry anything but a crop, a pest, a product
name, a date or a search string.
"""

from __future__ import annotations

from datetime import date

from . import lexicon
from .corpus import Corpus
from .harvest import safe_harvest
from .labels import LabelBook, per_unit_area


def _canon(value: str | None, finder) -> str | None:
    if not value:
        return None
    found = finder(str(value))
    return found[0] if found else None


def search_notes(corpus: Corpus, query: str, crop: str | None = None, pest: str | None = None) -> dict:
    crop = _canon(crop, lexicon.crops)
    pest = _canon(pest, lexicon.pests)
    notes = corpus.search(str(query)[:300], crop=crop, pest=pest)
    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
                "steps": list(n.steps_en),
                "steps_ne": list(n.steps_ne),
                "sources": list(n.sources),
            }
            for n in notes
        ]
    }


def pesticide_options(book: LabelBook, crop: str, pest: str | None = None) -> dict:
    c = _canon(crop, lexicon.crops)
    p = _canon(pest, lexicon.pests)
    if c is None:
        return {"crop": crop, "error": "unknown_crop", "options": []}
    options = []
    for r in book.options(c, p):
        rate = r.rate_per_ha()
        opt = {
            "chemical": r.chemical,
            "product": r.product,
            "pests_on_label": list(r.pests),
            # The crop's waiting period (longest across its label rows), not just this row's.
            "waiting_days": book.crop_waiting_days(r.chemical, c),
            "residue_test_target": r.chemical in lexicon.ORGANOPHOSPHATE_OR_CARBAMATE,
            "source": r.source,
        }
        if rate:
            area = per_unit_area(rate)
            opt.update(
                rate_per_ha=f"{r.product_per_ha} {r.unit}",
                per_ropani=_range(area["ropani"], r.unit),
                per_kattha=_range(area["kattha"], r.unit),
            )
        options.append(opt)
    banned_on_label = sorted(
        {r.chemical for r in book.rows if r.crop == c and book.ban(r.chemical) and (p is None or p in r.pests)}
    )
    return {"crop": c, "pest": p, "options": options, "banned_in_nepal_but_on_indian_label": banned_on_label}


def _range(lo_hi: tuple[float, float], unit: str) -> str:
    lo, hi = lo_hi
    return f"{_num(lo)} {unit}" if lo == hi else f"{_num(lo)}-{_num(hi)} {unit}"


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def chemical_status(book: LabelBook, chemical: str) -> dict:
    c = _canon(chemical, lexicon.chemicals)
    if c is None:
        return {"chemical": chemical, "known": False}
    ban = book.ban(c)
    crops = sorted({r.crop for r in book.rows_for(c)})
    return {
        "chemical": c,
        "known": True,
        "banned_in_nepal": bool(ban),
        "banned_year": ban.year if ban else None,
        "ban_note": ban.note if ban else "",
        "waiting_days_by_crop": {crop: book.crop_waiting_days(c, crop) for crop in crops},
    }


def safe_harvest_date(book: LabelBook, chemical: str, crop: str, spray_date: str, today: date) -> dict:
    c = _canon(chemical, lexicon.chemicals)
    k = _canon(crop, lexicon.crops)
    if c is None or k is None:
        return {"error": "unknown_chemical_or_crop", "chemical": chemical, "crop": crop}
    try:
        d = date.fromisoformat(str(spray_date)[:10])
    except ValueError:
        return {"error": "bad_date", "spray_date": spray_date}
    if d > today:
        return {"error": "spray_date_in_future", "spray_date": d.isoformat()}
    return safe_harvest(book, c, k, d, today)


SPECS = [
    {
        "name": "search_notes",
        "description": "Search Parkha's advisory notes (pest identification, non-chemical control, waiting periods, "
        "banned products, residue testing, safe handling). Returns up to 3 notes with ids to cite.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The farmer's question or key words, any language."},
                    "crop": {"type": "string"},
                    "pest": {"type": "string"},
                },
                "required": ["query"],
            }
        },
    },
    {
        "name": "pesticide_options",
        "description": "Insecticides on an official label for this crop and pest that are not banned in Nepal, "
        "with waiting period in days and rate per ropani and kattha. An empty list means Parkha has no verified option.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"crop": {"type": "string"}, "pest": {"type": "string"}},
                "required": ["crop"],
            }
        },
    },
    {
        "name": "chemical_status",
        "description": "Whether a pesticide (generic or brand name) is banned in Nepal, and its waiting period on each "
        "crop in the label table.",
        "inputSchema": {
            "json": {"type": "object", "properties": {"chemical": {"type": "string"}}, "required": ["chemical"]}
        },
    },
    {
        "name": "safe_harvest_date",
        "description": "The earliest safe harvest date after spraying a product on a crop. spray_date is YYYY-MM-DD; "
        "convert words like 'yesterday' or BS dates using today's date given in the system prompt.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "chemical": {"type": "string"},
                    "crop": {"type": "string"},
                    "spray_date": {"type": "string"},
                },
                "required": ["chemical", "crop", "spray_date"],
            }
        },
    },
]

_ALLOWED = {s["name"]: set(s["inputSchema"]["json"]["properties"]) for s in SPECS}


def bedrock_tool_config() -> dict:
    return {"tools": [{"toolSpec": s} for s in SPECS]}


def call(corpus: Corpus, book: LabelBook, today: date, name: str, args: dict) -> dict:
    if name not in _ALLOWED:
        return {"error": f"unknown tool {name}"}
    args = {k: v for k, v in (args or {}).items() if k in _ALLOWED[name]}
    try:
        if name == "search_notes":
            return search_notes(corpus, **args)
        if name == "pesticide_options":
            return pesticide_options(book, **args)
        if name == "chemical_status":
            return chemical_status(book, **args)
        return safe_harvest_date(book, today=today, **args)
    except TypeError as e:  # a required argument missing
        return {"error": f"bad arguments: {e}"}
