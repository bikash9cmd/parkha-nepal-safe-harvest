# Cost

About **$7 a month at 10,000 questions**, and the fixed CloudWatch alarms are a third of that.
Output of `python scripts/cost_model.py` (list prices in the script; check the AWS pricing pages
before quoting):

| Line | 1,000 / month | 10,000 / month | 100,000 / month |
|---|---:|---:|---:|
| Bedrock model (Nova Lite) | $0.20 | $1.96 | $19.61 |
| Bedrock guardrail (question only) | $0.23 | $2.29 | $22.86 |
| Lambda (arm64, 512 MB) | $0.02 | $0.17 | $1.69 |
| API Gateway, DynamoDB, logs | $0.00 | $0.04 | $0.40 |
| CloudWatch metrics (7) and alarms (5) | $2.60 | $2.60 | $2.60 |
| **Total** | **$3.05** | **$7.06** | **$47.15** |

## How the numbers are made

Sizes are measured from the code and the eval set: a 1,404-character system prompt, 1,637
characters of tool specs, a median of 3,466 characters of tool results per answered question,
and 360-character answers. Tokens are estimated from characters (4 per token for English and
JSON, 1.5 for Devanagari, assuming 60% of questions are in Nepali), with two tool rounds plus the
answer per advice question and a 10% rewrite rate. That is about 4,400 input and 320 output tokens
per question that reaches the model. These are estimates until `make eval-bedrock` records real
token counts.

## What each decision saved (10,000 questions a month)

| Decision | With it | Without it |
|---|---:|---:|
| Hybrid routing: harvest dates and ban status skip the model (ADR-004) | $7.06 | $10.24 |
| Nova Lite instead of Nova Pro (ADR-003) | $7.06 | $31.24 |
| Guardrail once on the question instead of attached to every call (ADR-005) | $7.06 | $34.48 |
| No vector store: BM25 over 13 notes (ADR-002) | $7.06 | $182.26 (OpenSearch Serverless) |
| Refusals before any model or guardrail call | crisis, harm, cosmetic and injection questions cost $0 | |

## Next levers, in order

1. **Trim tool results.** Search results are the biggest input: three full notes with English and
   Nepali steps. Sending the top two, and only the steps in the question's language, would cut
   input tokens by roughly a third.
2. **Drop the guardrail's PII filter.** Phone numbers are already redacted in code before logging;
   the filter is a quarter of the guardrail's per-unit price.
3. **Bedrock prompt caching** for the fixed part (system prompt and tool specs, about 760 tokens),
   after checking it is supported for Nova Lite through the APAC profile.

## Denial of wallet

An LLM endpoint is a billing endpoint. The HTTP API throttle (5 rps, burst 20), reserved
concurrency 10, 600 max output tokens, 4 tool rounds and 1 rewrite bound the worst case; the
TokenSpendAlarm (5 million input tokens a day) and the budget say when it is happening.
