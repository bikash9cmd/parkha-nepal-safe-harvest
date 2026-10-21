"""One question in, one checked answer out: screen -> backend -> gate -> rewrite -> fallback."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import date

from . import answer, bedrock, config, gate, guard, prompts, router
from .corpus import Corpus, default_corpus
from .labels import LabelBook, default_book

log = logging.getLogger(__name__)

SAFE_DEFAULT = {
    "en": "I can't give you a checked answer to that. Please ask your Agriculture Knowledge Centre, and do not "
    "harvest anything you sprayed until the label waiting period has passed.",
    "ne": "यसको जाँच गरिएको जवाफ म दिन सक्दिनँ। कृपया कृषि ज्ञान केन्द्रमा सोध्नुहोस्, र छरेको तरकारी लेबलको पर्खने अवधि "
    "पूरा नभई नटिप्नुहोस्।",
}


# Question shapes the offline router answers exactly; in hybrid mode they never reach the model.
DETERMINISTIC = {"harvest", "harvest_needs_date", "status"}


@dataclass
class Reply:
    answer: str
    language: str
    backend: str
    today: str
    route: str = "rules"
    refusal: str | None = None
    fallback: str | None = None
    rewrites: int = 0
    gate_problems: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    log_question: bool = True

    def public(self, debug: bool = False) -> dict:
        d = asdict(self)
        d.pop("log_question")
        if not debug:
            for k in ("tool_calls", "tool_results", "gate_problems"):
                d.pop(k)
        return d


def _sources(results: list[dict], book: LabelBook) -> list[dict]:
    ids: list[str] = []
    for r in results:
        for n in r.get("notes", [])[:1]:  # the note the answer is built on
            ids += [s for s in n["sources"] if s not in ids]
        for o in r.get("options", [])[:3]:
            if o["source"] not in ids:
                ids.append(o["source"])
        if r.get("banned_in_nepal") is not None and r.get("chemical"):
            ban = book.ban(r["chemical"])
            for s in ban.source.split(";") if ban else []:
                if s not in ids:
                    ids.append(s)
        if "earliest_harvest" in r:
            for row in book.rows_for(r["chemical"], r["crop"]):
                if row.source not in ids:
                    ids.append(row.source)
    return [
        {"id": i, "title": book.sources[i]["title"], "url": book.sources[i]["url"]} for i in ids if i in book.sources
    ]


def _rules(question: str, corpus: Corpus, book: LabelBook, today: date) -> tuple[str, list[dict], list]:
    r = router.answer_question(question, corpus, book, today)
    problems = gate.check(r.text, gate.Context(question, today, r.results), book)
    if problems:
        # A template that fails the gate is a bug, and it never reaches a farmer.
        log.error("template failed the gate: %s", [p.detail for p in problems])
        return SAFE_DEFAULT[router.language(question)], r.results, r.calls
    return r.text, r.results, r.calls


def ask(
    question: str,
    backend: str = "rules",
    client=None,
    today: date | None = None,
    corpus: Corpus | None = None,
    book: LabelBook | None = None,
    model_id: str = config.MODEL_ID,
    guardrail: tuple[str, str] | None = None,
) -> Reply:
    t0 = time.perf_counter()
    question = (question or "").strip()
    today = today or config.today_npt()
    corpus = corpus or default_corpus()
    book = book or default_book()
    lang = router.language(question)
    reply = Reply(answer="", language=lang, backend=backend, today=today.isoformat())

    s = guard.screen(question)
    if s.kind == "crisis":
        reply.answer, reply.refusal, reply.log_question = answer.crisis(lang), "crisis", False
    elif s.kind != "ok":
        reply.answer, reply.refusal = answer.refusal(s.kind, lang), s.kind
    elif backend == "hybrid" and router.answer_question(question, corpus, book, today).intent in DETERMINISTIC:
        # Harvest dates and ban status are arithmetic and lookups: the template is exact, and a model
        # can only add risk and cost. Only free-form advice goes to the model (ADR-004).
        reply.route = "rules"
        reply.answer, reply.tool_results, reply.tool_calls = _rules(question, corpus, book, today)
    elif backend in ("bedrock", "hybrid"):
        reply.route = "bedrock"
        _bedrock(reply, question, client, today, corpus, book, model_id, guardrail)
    else:
        reply.answer, reply.tool_results, reply.tool_calls = _rules(question, corpus, book, today)

    reply.sources = _sources(reply.tool_results, book)
    reply.latency_ms = int((time.perf_counter() - t0) * 1000)
    return reply


def _bedrock(reply: Reply, question, client, today, corpus, book, model_id, guardrail) -> None:
    client = client or bedrock.client()
    try:
        if guardrail:
            blocked = bedrock.apply_guardrail(client, guardrail[0], guardrail[1], question)
            if blocked:
                reply.answer, reply.refusal = blocked, "guardrail"
                return
        session = bedrock.BedrockSession(client, corpus, book, today, prompts.system(today), model_id=model_id)
        text = session.say(question)
        problems = gate.check(text, gate.Context(question, today, session.tool_results), book)
        while problems and reply.rewrites < config.MAX_REWRITES:
            reply.rewrites += 1
            reply.gate_problems.append([f"{p.rule}: {p.detail}" for p in problems])
            text = session.say(prompts.rewrite([p.detail for p in problems]))
            problems = gate.check(text, gate.Context(question, today, session.tool_results), book)
        reply.tool_calls, reply.tool_results = session.tool_calls, session.tool_results
        reply.input_tokens, reply.output_tokens = session.usage.input_tokens, session.usage.output_tokens
        if problems:
            reply.gate_problems.append([f"{p.rule}: {p.detail}" for p in problems])
            reply.fallback = "gate"
        else:
            reply.answer = text
            return
    except bedrock.TooManyToolRounds:
        reply.fallback = "tool_rounds"
    except Exception as e:  # throttling, timeouts, access denied: the farmer still gets an answer
        log.warning("bedrock failed: %s", e)
        reply.fallback = type(e).__name__
    reply.answer, reply.tool_results, reply.tool_calls = _rules(question, corpus, book, today)
