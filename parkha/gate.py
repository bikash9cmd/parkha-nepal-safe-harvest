"""The safety gate: every answer is checked against what the tools returned before anyone sees it.

A fluent wrong answer here is not a bad user experience, it is a poisoned meal. The gate is
deterministic and runs on every answer, from the model or from the templates:

1. banned      a product banned in Nepal is named outside a "banned / do not use" sentence
2. unknown     a product is named that no tool returned and no retrieved note mentions
3. number      a number appears that is not in the question, the tool results or the notes
   dose        a rate (ml or g) that is not a rate returned for the product named before it
4. waiting     "<product> ... N days" where N is not that product's waiting period, or a
               waiting period in words ("a couple of days") next to a product
5. required    the harvest date (when one was computed), or the waiting period of each
               recommended product, is missing
6. unsafe      washing removes it, no need to wait, harvest straight away, mix products
7. date        a date that is not the spray date, the harvest date or today

It only knows the products in the lexicon. A product it has never heard of passes rule 2 by
being invisible, which is why rule 3 still stops any waiting period or dose quoted for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from . import dates, lexicon
from .labels import LabelBook

_SENTENCE = re.compile(r"[^.!?।\n]+[.!?।]?")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w])")
_DAYS = re.compile(r"(\d+)\s*(?:-|to)?\s*(?:days?|din|दिन)", re.I)
_BAN_WORDS = re.compile(
    r"\b(banned|ban|prohibited|not allowed|illegal|do not (use|buy)|don'?t (use|buy)|never use|avoid)\b"
    r"|प्रतिबन्ध|प्रतिबन्धित|नकिन्नु|प्रयोग नगर्नु|गैरकानुनी|नछर्नु",
    re.I,
)
_UNSAFE = [
    (
        "washing",
        re.compile(r"\bwash\w*\b.{0,40}\b(remov|safe|clean|enough|gets rid)\w*|पखाल्दा.{0,30}(हट्छ|सुरक्षित)", re.I),
    ),
    ("no_wait", re.compile(r"\bno (need to )?wait\w*|\bwithout waiting\b|पर्खनु पर्दैन|पर्खन पर्दैन", re.I)),
    (
        "harvest_now",
        re.compile(
            r"\b(harvest|pick|sell)\w* (it |them )?(the same day|right away|immediately|straight away)|तुरुन्तै टिप", re.I
        ),
    ),
    ("mixing", re.compile(r"(?<!not )(?<!n't )\bmix (it |them )?(with|together)\b|सँगै मिसाएर छर्नु", re.I)),
    ("absolute_safety", re.compile(r"\b(100% safe|completely safe|totally safe|perfectly safe)\b|पूर्ण सुरक्षित", re.I)),
]
_DOSE = re.compile(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*(?:ml|g|मिलि|ग्राम)(?![a-z])", re.I)
_WORD_DAYS = re.compile(
    r"(?<!twice )(?<!once )(?<!times )\b(one|two|three|four|five|six|seven|eight|nine|ten|a couple of|a few|a|one or two)\s+(days?|weeks?)\b"
    r"|(एक|दुई|तीन|चार|पाँच|छ|सात|आठ|नौ|दस|केही|एक\-दुई)\s+(दिन|हप्ता)",
    re.I,
)
_ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
_EN_DATE = re.compile(
    r"\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (20\d\d)\b"
)


@dataclass
class Problem:
    rule: str
    detail: str


@dataclass
class Context:
    """What the answer is allowed to rest on."""

    question: str
    today: date
    results: list[dict] = field(default_factory=list)

    def harvests(self) -> list[dict]:
        return [r for r in self.results if "earliest_harvest" in r]

    def options(self) -> list[dict]:
        return [o for r in self.results for o in r.get("options", [])]

    def notes_text(self) -> str:
        return "\n".join(
            n["title"] + " " + n["summary"] + " " + " ".join(n["steps"] + n.get("steps_ne", []))
            for r in self.results
            for n in r.get("notes", [])
        )

    def waiting_by_chemical(self, book: LabelBook) -> dict[str, set[int]]:
        out: dict[str, set[int]] = {}
        for o in self.options():
            if o.get("waiting_days") is not None:
                out.setdefault(o["chemical"], set()).add(o["waiting_days"])
        # chemical_status lists a product's waiting period on every crop. Only the crops this question is
        # about count, or neem's 7 days on cabbage would excuse "7 days" on cauliflower (bug #11).
        crops = set(lexicon.crops(self.question)) | {r["crop"] for r in self.results if r.get("crop")}
        for r in self.results:
            for crop, d in (r.get("waiting_days_by_crop") or {}).items():
                if d is not None and r.get("chemical") and (not crops or crop in crops):
                    out.setdefault(r["chemical"], set()).add(d)
            if "earliest_harvest" in r and r.get("waiting_days") is not None:
                out.setdefault(r["chemical"], set()).add(r["waiting_days"])
        return out


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in _NUMBER.findall(dates.ascii_digits(text))}


def _norm(n: str) -> str:
    return str(float(n)).rstrip("0").rstrip(".")


def _flatten(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten(v) for v in obj)
    return str(obj)


def _allowed_numbers(ctx: Context) -> set[str]:
    text = ctx.question + " " + " ".join(_flatten(r) for r in ctx.results) + " " + dates.fmt_en(ctx.today)
    text += " " + dates.fmt_ne(ctx.today) + " " + ctx.today.isoformat()
    allowed = _numbers(text)
    for r in ctx.harvests():
        allowed |= _numbers(r["earliest_harvest_en"] + " " + r["earliest_harvest_ne"] + " " + r["spray_date"])
        sd = date.fromisoformat(r["spray_date"])
        allowed |= _numbers(dates.fmt_en(sd) + " " + dates.fmt_ne(sd))
    allowed |= {"1", "2"}  # "one product", "two sprays": counting words written as digits
    return allowed


def _allowed_dates(ctx: Context) -> set[date]:
    out = {ctx.today}
    for r in ctx.harvests():
        out |= {date.fromisoformat(r["earliest_harvest"]), date.fromisoformat(r["spray_date"])}
    qd = dates.parse_spray_date(ctx.question, ctx.today)
    if qd:
        out.add(qd)
    return out


def _date_present(answer: str, d: date) -> bool:
    a = dates.ascii_digits(answer)
    b = dates.bs(d)
    month_en = d.strftime("%B")
    bs_en = dates.BS_MONTHS_EN[b.month - 1]
    bs_ne = dates.BS_MONTHS_NE[b.month - 1]
    patterns = [
        d.isoformat(),
        f"{d.day} {month_en}",
        f"{month_en} {d.day}",
        f"{b.day} {bs_en}",
        f"{bs_en} {b.day}",
        f"{bs_ne} {b.day}",
        f"{b.day} {bs_ne}",
    ]
    return any(re.search(r"(?<!\d)" + re.escape(p) + r"(?!\d)", a) for p in patterns)


def check(answer: str, ctx: Context, book: LabelBook) -> list[Problem]:
    problems: list[Problem] = []
    sentences = [s for s in _SENTENCE.findall(answer) if s.strip()]
    notes_and_question = ctx.notes_text() + " " + ctx.question
    looked_up = {r.get("chemical") for r in ctx.results if r.get("chemical")} | {o["chemical"] for o in ctx.options()}
    in_notes = set(lexicon.chemicals(notes_and_question))
    waiting = ctx.waiting_by_chemical(book)
    named: set[str] = set()

    for s in sentences:
        chems = lexicon.chemicals(s)
        named.update(chems)
        for c in chems:
            if book.ban(c) and not _BAN_WORDS.search(s):
                problems.append(
                    Problem("banned", f"{c} is banned in Nepal and is named without saying so: {s.strip()!r}")
                )
            elif not book.ban(c) and c not in looked_up and c not in in_notes:
                problems.append(Problem("unknown", f"{c} was not returned by any tool or note"))
        # Rule 4: a waiting period belongs to the product named closest before it in the same sentence.
        # (It first applied only to sentences naming one product, so two products' waiting periods
        # swapped inside a list passed: every number was real and present.)
        s_ascii = dates.ascii_digits(s)
        s_mentions = lexicon.chemical_mentions(s_ascii)
        for m in _DAYS.finditer(s_ascii):
            before = [x for x in s_mentions if x.end <= m.start()]
            c = before[-1].canonical if before else (chems[0] if len(chems) == 1 else None)
            if c in waiting and not book.ban(c) and int(m.group(1)) not in waiting[c]:
                problems.append(Problem("waiting", f"{c}: {m.group(1)} days, label says {sorted(waiting[c])}"))

    # Rule 3b: a rate (a number with ml or g) must be one of the rates returned for the product named
    # just before it. Plain membership let a x10 dose through whenever the bigger number happened
    # to be some other figure in the results (bug #12).
    a_ascii = dates.ascii_digits(answer)
    mentions = lexicon.chemical_mentions(a_ascii)
    rates: dict[str, set[str]] = {}
    for o in ctx.options():
        for k in ("per_ropani", "per_kattha", "rate_per_ha"):
            if o.get(k):
                rates.setdefault(o["chemical"], set()).update(_numbers(o[k]))
    for m in _DOSE.finditer(a_ascii):
        before = [x for x in mentions if x.end <= m.start()]
        chem = before[-1].canonical if before else None
        got = {_norm(x) for x in m.groups()[:2] if x}
        if chem is None or not got <= rates.get(chem, set()):
            problems.append(Problem("dose", f"{m.group(0).strip()} is not a returned rate for {chem or 'any product'}"))

    allowed = _allowed_numbers(ctx)
    for n in sorted(_numbers(answer) - allowed):
        problems.append(Problem("number", f"{n} is not in the question, the tool results or the notes"))

    ok_dates = _allowed_dates(ctx)
    a = dates.ascii_digits(answer)
    for m in _ISO.finditer(a):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d not in ok_dates:
            problems.append(Problem("date", f"{d} is not the spray date, the harvest date or today"))
    for m in _EN_DATE.finditer(a):
        d = date(int(m.group(3)), _month(m.group(2)), int(m.group(1)))
        if d not in ok_dates:
            problems.append(Problem("date", f"{d} is not the spray date, the harvest date or today"))

    # Rule 5: the figures that answer the question must be there.
    for h in ctx.harvests():
        if h["chemical"] in named or len(ctx.harvests()) == 1:
            if not _date_present(answer, date.fromisoformat(h["earliest_harvest"])):
                problems.append(Problem("required", f"the earliest harvest date {h['earliest_harvest']} is missing"))
    for c in named:
        if c in waiting and not book.ban(c) and not any(str(d) in _numbers(answer) for d in waiting[c]):
            problems.append(Problem("required", f"{c} is named without its waiting period"))
    for r in ctx.results:
        if r.get("banned_in_nepal") and r.get("chemical") in lexicon.chemicals(ctx.question):
            if not _BAN_WORDS.search(answer):
                problems.append(
                    Problem(
                        "required", f"the question asks about {r['chemical']}, which is banned; the answer must say so"
                    )
                )

    # Rule 4b: a waiting period in words ("two days", "a week") cannot be checked, so it is not allowed
    # in a sentence that names a product. The templates and the prompt always use digits.
    for s in sentences:
        if lexicon.chemicals(s) and _WORD_DAYS.search(s):
            problems.append(Problem("waiting", f"waiting period in words: {_WORD_DAYS.search(s).group(0)!r}"))

    for rule, pat in _UNSAFE:
        if pat.search(answer):
            if rule == "harvest_now" and any(h["status"] == "ok_to_harvest" for h in ctx.harvests()):
                continue
            problems.append(Problem("unsafe", rule))
    return problems


def _month(name: str) -> int:
    return [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ].index(name) + 1  # fmt: skip
