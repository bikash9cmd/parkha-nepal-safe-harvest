"""The offline backend: a rule-based reading of the question that calls the same tools.

It is the backend for local runs, CI and the evaluation, and the fallback's source of tool
results when the model fails. It understands three shapes of question:

- harvest   a product, a crop and a spray date (or "when can I harvest")
- status    a product on its own ("is Furadan banned?")
- advice    a crop and/or a pest ("गोलभेडामा टुटा लाग्यो")

and falls back to searching the notes for anything else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from . import answer, dates, lexicon, tools
from .corpus import Corpus
from .labels import LabelBook

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_ROMAN_NE = re.compile(
    r"\b(ma|ko|lai|chha|chhan|cha|garne|garnu|kati|kahile|din|chhare|chhareko|chharen|bali|kira|lagyo|lageko|"
    r"tipna|tipne|bechna|sakinchha|parcha|hunchha|ho|haina|kun|ke|bhane|khayo|garda|malai|mero|hamro|pani|milchha)\b",
    re.I,
)
_HARVEST_WORDS = re.compile(
    r"\b(harvest|pick|sell|market|sprayed|spray(ed)? on|tip\w*|bech\w*|chhar\w*|kahile)\b|टिप|बेच|छरें|छरेको|छर्यो|छरे|कहिले",
    re.I,
)


# Romanised Nepali crop and pest names: one of these plus one grammar word is enough.
_ROMAN_NAMES = re.compile(
    r"\b(golbh\w*|banda\w*|kauli|bhanta|bhindi|khursani|akabare|kakro|kankro|karela|simi|makai|dhan|fauji|lahi"
    r"|sulsule|gabaro|hire putali|aunsa|seto jhinga)\b",
    re.I,
)


def language(question: str) -> str:
    if _DEVANAGARI.search(question):
        return "ne"
    grammar = len(_ROMAN_NE.findall(question))
    return "ne" if grammar >= 2 or (grammar and _ROMAN_NAMES.search(question)) else "en"


@dataclass
class RulesResult:
    text: str
    intent: str
    calls: list = field(default_factory=list)
    results: list = field(default_factory=list)


def answer_question(question: str, corpus: Corpus, book: LabelBook, today: date) -> RulesResult:
    lang = language(question)
    crops = lexicon.crops(question)
    pests = lexicon.pests(question)
    chems = lexicon.chemicals(question)
    crop = crops[0] if crops else None
    pest = pests[0] if pests else None
    out = RulesResult(text="", intent="")

    def call(name: str, **args):
        r = tools.call(corpus, book, today, name, args)
        out.calls.append((name, args))
        out.results.append(r)
        return r

    if chems and crop and _HARVEST_WORDS.search(question):
        spray = dates.parse_spray_date(question, today)
        if spray:
            h = call("safe_harvest_date", chemical=chems[0], crop=crop, spray_date=spray.isoformat())
            if "error" not in h:
                out.intent, out.text = "harvest", answer.harvest(h, lang)
                return out
        s = call("chemical_status", chemical=chems[0])
        out.intent, out.text = "harvest_needs_date", answer.need_date(s, crop, lang)
        if s.get("banned_in_nepal"):
            out.text += " " + answer.status(s, lang).split(". ")[0] + "."
        return out

    if chems and not crop and not pest:
        s = call("chemical_status", chemical=chems[0])
        out.intent, out.text = "status", answer.status(s, lang)
        return out

    notes = call("search_notes", query=question, crop=crop, pest=pest)["notes"]
    opts = call("pesticide_options", crop=crop, pest=pest) if crop else None
    if chems:
        s = call("chemical_status", chemical=chems[0])
        if s.get("banned_in_nepal"):
            out.intent = "advice"
            out.text = answer.status(s, lang).split(". ")[0] + ". " + answer.advice(notes, opts, crop, pest, lang)
            return out
    out.intent = "advice" if (crop or pest) else "general"
    out.text = answer.advice(notes, opts, crop, pest, lang)
    return out
