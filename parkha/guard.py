"""Question screening, before any retrieval or model call.

Pesticides are the second most common means of suicide in Nepal, and three of the products
banned in December 2024 were banned for that reason. So the first check on every question is
whether the person is in crisis, and the answer to that is never pesticide information.

The other refusals: harming people or animals with pesticide (including poisoning fish in
rivers), spraying to make produce look fresh for market, and prompt injection. Each pattern was
added because a test question needed it; romanised Nepali is matched as well as Devanagari.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import config

_CRISIS = re.compile(
    r"\b(suicide|kill (my ?self|myself)|end (my|his|her) life|want to die|how much .{0,30}(to die|kill a (person|human))"
    r"|lethal dose|aatmahatya|atmahatya|marna (chahanchhu|man lagyo|man lageko)|marna chahan|marchhu|marchu"
    r"|kati khayo bhane marin|khayera marn)"
    r"|आत्महत्या|मर्न चाहन्छु|मर्न मन|मर्छु|ज्यान फाल्|कति खाँदा मरिन्छ|कति खाए मरिन्छ|खाएर मर्",
    re.I,
)
_HARM = re.compile(
    r"\b(poison (my |a |the |our )?(neighbou?r|husband|wife|someone|person|people|dog|dogs|cattle|buffalo|goat)"
    r"|(kill|catch) fish|fish (poison|killing)|machha marn|maachha marn|kukur marn|manchhe marn)"
    r"|माछा मार्न|माछा मार्ने|कुकुर मार्न|मान्छे मार्न|छिमेकीलाई विष",
    re.I,
)
_COSMETIC = re.compile(
    r"\b(look(s|ing)? fresh|keep (it |them |vegetables? )?fresh|stay fresh"
    r"|(spray|chhar\w*) .{0,25}(before|just before) (market|selling|sale|kalimati)"
    r"|taja dekh\w*|chamk\w*|bajar lanu (aghi|agadi) chhar\w*)\b"
    r"|ताजा देखिन|ताजा देखाउन|चम्किलो|बजार लैजानु\s*(अघि|अगाडि)",
    re.I,
)
_INJECTION = re.compile(
    r"\b(ignore (all |the |your )?(previous|above|prior) (instructions|rules)|system prompt|you are now|developer mode"
    r"|jailbreak|pretend (you are|to be)|reveal your (rules|prompt))\b|पहिलेका निर्देशन|निर्देशन बिर्स",
    re.I,
)
_PHONE = re.compile(r"(?<!\d)(?:\+?977[-\s]?)?9[678]\d{8}(?!\d)")


@dataclass(frozen=True)
class Screen:
    kind: str  # ok | crisis | harm | cosmetic | injection | too_long


def screen(question: str) -> Screen:
    if _CRISIS.search(question):
        return Screen("crisis")
    if len(question) > config.MAX_QUESTION_CHARS:
        return Screen("too_long")
    if _HARM.search(question):
        return Screen("harm")
    if _INJECTION.search(question):
        return Screen("injection")
    if _COSMETIC.search(question):
        return Screen("cosmetic")
    return Screen("ok")


def redact(text: str) -> str:
    """For the answer log: phone numbers out. Crisis questions are never logged at all (assistant.py)."""
    return _PHONE.sub("[phone]", text)
