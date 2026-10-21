"""Monthly cost model behind docs/COST.md.

Prompt, tool-spec and tool-result sizes are measured from the code and from real tool results on
the evaluation set; tokens are estimated from characters (Nova's tokenizer is not available
offline). Prices are list prices in one place, so they are easy to update. Check the AWS pricing
pages before quoting these numbers.

    python scripts/cost_model.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parkha import assistant, prompts, router, tools  # noqa: E402
from parkha.corpus import default_corpus  # noqa: E402
from parkha.labels import default_book  # noqa: E402

TODAY = date(2026, 10, 21)

PRICES = {
    # Amazon Nova Lite on Bedrock, on-demand, per 1,000 tokens. Nova Pro for comparison.
    "nova_lite_in": 0.00006,
    "nova_lite_out": 0.00024,
    "nova_pro_in": 0.0008,
    "nova_pro_out": 0.0032,
    # Titan Text Embeddings V2, per 1,000 tokens (only in the "embeddings" alternative).
    "titan_embed": 0.00002,
    # Bedrock Guardrails per 1,000 text units (a text unit is up to 1,000 characters).
    "guardrail_content_filter": 0.15,
    "guardrail_denied_topics": 0.15,
    "guardrail_pii": 0.10,
    # Lambda arm64 per GB-second and per million requests; HTTP API and DynamoDB per million.
    "lambda_gb_s": 0.0000133334,
    "lambda_req": 0.20 / 1e6,
    "http_api": 1.00 / 1e6,
    "ddb_write": 1.25 / 1e6,
    # CloudWatch: per custom metric, per alarm, per GB of logs.
    "cw_metric": 0.30,
    "cw_alarm": 0.10,
    "cw_logs_gb": 0.50,
    # OpenSearch Serverless (the classic Knowledge Base vector store): per OCU-hour, 1 OCU minimum
    # in dev mode (0.5 indexing + 0.5 search).
    "aoss_ocu_hour": 0.24,
}

CHARS_PER_TOKEN_EN = 4.0
CHARS_PER_TOKEN_NE = 1.5  # Devanagari splits into far more tokens; a conservative guess


def measured() -> dict:
    items = [json.loads(line) for line in open(ROOT / "eval/questions.jsonl", encoding="utf-8")]
    results, answers, calls, deterministic = [], [], [], 0
    for item in items:
        r = assistant.ask(item["q"], today=TODAY)
        if r.refusal:
            continue
        intent = router.answer_question(item["q"], default_corpus(), default_book(), TODAY).intent
        deterministic += intent in assistant.DETERMINISTIC
        results.append(sum(len(json.dumps(x, ensure_ascii=False)) for x in r.tool_results))
        answers.append(len(r.answer))
        calls.append(len(r.tool_calls))
    return {
        "system_chars": len(prompts.system(TODAY)),
        "tool_spec_chars": len(json.dumps(tools.bedrock_tool_config())),
        "tool_result_chars": statistics.median(results),
        "answer_chars": statistics.median(answers),
        "tool_calls": statistics.mean(calls),
        "answered_share": len(calls) / len(items),
        # In hybrid mode these never reach the model (harvest dates and ban status).
        "deterministic_share": deterministic / len(calls),
    }


def per_question(m: dict, share_nepali=0.6, rewrite_rate=0.1, model="nova_lite", guard_once=True) -> dict:
    cpt = 1 / ((1 - share_nepali) / CHARS_PER_TOKEN_EN + share_nepali / CHARS_PER_TOKEN_NE)
    fixed = (m["system_chars"] + m["tool_spec_chars"]) / CHARS_PER_TOKEN_EN
    question = 80 / cpt
    results = m["tool_result_chars"] / CHARS_PER_TOKEN_EN  # JSON, mostly English keys and notes
    answer = m["answer_chars"] / cpt
    # Converse calls: one per tool round (the model asks for tools in up to two rounds) plus the answer.
    rounds = 2
    calls = rounds + 1
    # Each call re-sends everything so far: the fixed part every time, results after they arrive.
    tokens_in = calls * (fixed + question) + (rounds - 1 + 1) * results + rounds * 60
    tokens_out = rounds * 60 + answer
    if rewrite_rate:
        tokens_in += rewrite_rate * (fixed + question + results + answer + 80)
        tokens_out += rewrite_rate * answer
    model_cost = tokens_in / 1000 * PRICES[f"{model}_in"] + tokens_out / 1000 * PRICES[f"{model}_out"]
    # Guardrail on the question only (1 text unit), or attached to every call (input and output of each).
    g = PRICES["guardrail_content_filter"] + PRICES["guardrail_denied_topics"] + PRICES["guardrail_pii"]
    if guard_once:
        guard_units = 1
    else:
        guard_units = sum(-(-int(x * cpt) // 1000) for x in [fixed + question] * calls + [results] * rounds) + calls
    return {
        "tokens_in": round(tokens_in),
        "tokens_out": round(tokens_out),
        "model": model_cost,
        "guardrail": guard_units * g / 1000,
    }


def monthly(questions: int, m: dict, hybrid: bool = True, **kw) -> dict:
    q = per_question(m, **kw)
    # Conservative: every question is assumed answerable (the eval set over-represents refusals, which
    # cost nothing). In hybrid mode the deterministic share skips the model. That share comes from
    # the eval set's mix of questions, which is my guess at real traffic, not a measurement of it.
    to_model = questions * ((1 - m["deterministic_share"]) if hybrid else 1)
    lines = {
        "Bedrock model": to_model * q["model"],
        "Bedrock guardrail": to_model * q["guardrail"],
        "Lambda": questions * (0.5 * 2.5 * PRICES["lambda_gb_s"] + PRICES["lambda_req"]),
        "API Gateway": questions * PRICES["http_api"],
        "DynamoDB": questions * 1.2 * PRICES["ddb_write"],
        "CloudWatch metrics (7) and alarms (5)": 7 * PRICES["cw_metric"] + 5 * PRICES["cw_alarm"],
        "CloudWatch logs": questions * 3000 / 1e9 * PRICES["cw_logs_gb"],
    }
    lines["Total"] = sum(lines.values())
    return lines


def main() -> None:
    m = measured()
    print("Measured sizes:", json.dumps({k: round(v, 2) for k, v in m.items()}))
    q = per_question(m)
    print(f"Per question (Nova Lite): ~{q['tokens_in']} input and ~{q['tokens_out']} output tokens")
    for n in (1_000, 10_000, 100_000):
        lines = monthly(n, m)
        print(f"\n{n:,} questions a month")
        for k, v in lines.items():
            print(f"  {k:42s} ${v:9.2f}")
    print("\nAlternatives at 10,000 questions a month:")
    base = monthly(10_000, m)["Total"]
    every = monthly(10_000, m, hybrid=False)["Total"]
    pro = monthly(10_000, m, model="nova_pro")["Total"]
    attached = monthly(10_000, m, guard_once=False)["Total"]
    kb_aoss = base + 730 * PRICES["aoss_ocu_hour"]
    print(f"  Parkha as designed                      ${base:9.2f}")
    print(f"  Every question to the model (no hybrid) ${every:9.2f}")
    print(f"  Nova Pro instead of Nova Lite           ${pro:9.2f}")
    print(f"  Guardrail attached to every call        ${attached:9.2f}")
    print(f"  + Knowledge Base on OpenSearch Serverless ${kb_aoss:7.2f}")


if __name__ == "__main__":
    main()
