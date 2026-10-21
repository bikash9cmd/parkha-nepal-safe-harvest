from botocore.exceptions import ClientError

from parkha import assistant
from tests.fakes import ScriptedBedrock, text, tool_use

Q = "I sprayed chlorantraniliprole on my brinjal yesterday. When can I harvest?"
GOOD = (
    "Chlorantraniliprole has a 22 day waiting period on brinjal. You sprayed on 20 October 2026, so the earliest "
    "safe harvest is 11 November 2026. Please confirm with your Agriculture Knowledge Centre."
)
BAD = "Chlorantraniliprole needs only 3 days on brinjal, so you can harvest from 23 October 2026."


def _ask(client, today, q=Q, **kw):
    return assistant.ask(q, backend="bedrock", client=client, today=today, **kw)


def harvest_call():
    return tool_use("safe_harvest_date", chemical="chlorantraniliprole", crop="brinjal", spray_date="2026-10-20")


def test_good_answer_passes(today):
    client = ScriptedBedrock(harvest_call(), text(GOOD))
    r = _ask(client, today)
    assert r.answer == GOOD and r.fallback is None and r.rewrites == 0
    # The tool result reached the model.
    sent = client.requests[1]["messages"][-1]["content"][0]["toolResult"]["content"][0]["json"]
    assert sent["earliest_harvest"] == "2026-11-11"
    assert r.input_tokens == 2100 and r.output_tokens == 120


def test_bad_answer_is_rewritten_once(today):
    client = ScriptedBedrock(harvest_call(), text(BAD), text(GOOD))
    r = _ask(client, today)
    assert r.answer == GOOD and r.rewrites == 1
    rewrite = client.requests[2]["messages"][-1]["content"][0]["text"]
    assert "3 days" in rewrite and "label says [22]" in rewrite


def test_bad_twice_falls_back_to_the_template(today):
    client = ScriptedBedrock(harvest_call(), text(BAD), text(BAD))
    r = _ask(client, today)
    assert r.fallback == "gate" and "11 November 2026" in r.answer and "22 days" in r.answer


def test_throttling_falls_back(today):
    err = ClientError({"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse")
    r = _ask(ScriptedBedrock(error=err), today)
    assert r.fallback == "ClientError" and "11 November 2026" in r.answer


def test_tool_loop_falls_back(today):
    client = ScriptedBedrock(*[harvest_call() for _ in range(5)])
    r = _ask(client, today)
    assert r.fallback == "tool_rounds"


def test_guardrail_runs_once_on_the_question(today):
    client = ScriptedBedrock(harvest_call(), text(GOOD))
    _ask(client, today, guardrail=("gr-1", "1"))
    assert len(client.guardrail_requests) == 1
    assert client.guardrail_requests[0]["source"] == "INPUT"
    assert all("guardrailConfig" not in req for req in client.requests)


def test_guardrail_block(today):
    r = _ask(ScriptedBedrock(guardrail_blocks=True), today, guardrail=("gr-1", "1"))
    assert r.refusal == "guardrail"


def test_crisis_never_reaches_bedrock(today):
    client = ScriptedBedrock()
    r = _ask(client, today, q="मर्न मन लाग्यो", guardrail=("gr-1", "1"))
    assert r.refusal == "crisis" and client.requests == [] and client.guardrail_requests == []


def test_unknown_tool_arguments_are_dropped(today):
    call = tool_use("chemical_status", chemical="Furadan", sql="DROP TABLE labels")
    client = ScriptedBedrock(call, text("Furadan is carbofuran, banned in Nepal since 2019. Do not use it."))
    r = _ask(client, today, q="Is Furadan banned?")
    assert r.tool_results[0]["chemical"] == "carbofuran" and r.fallback is None


def test_hybrid_answers_harvest_questions_without_the_model(today):
    client = ScriptedBedrock()
    r = assistant.ask(Q, backend="hybrid", client=client, today=today)
    assert r.route == "rules" and client.requests == [] and "11 November 2026" in r.answer


def test_hybrid_sends_advice_to_the_model(today):
    good = (
        "Hang yellow sticky traps and spray water on the colonies. If needed, acetamiprid is on the okra label "
        "with a 3 day waiting period. Confirm with your Agriculture Knowledge Centre."
    )
    client = ScriptedBedrock(tool_use("pesticide_options", crop="okra", pest="aphid"), text(good))
    r = assistant.ask("okra aphid", backend="hybrid", client=client, today=today)
    assert r.route == "bedrock" and r.answer == good
