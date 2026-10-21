# What breaks, and what happens then

| # | Failure | How it's detected | What the farmer gets | Covered by |
|---|---|---|---|---|
| 1 | Bedrock throttles, times out or denies access | botocore exception | The template answer from the same tools, a little plainer | `test_throttling_falls_back`; `FallbackAlarm` |
| 2 | The model loops on tool calls | more than 4 tool rounds | Template answer | `test_tool_loop_falls_back` |
| 3 | The model gives the wrong waiting period, or one product's period for another | gate rule 4 | One rewrite with the reason; if it fails again, the template | `test_bad_answer_is_rewritten_once`, mutation test (`waiting_off`, `waiting_swapped`, `both_swapped`) |
| 4 | The model gives a harvest date a few days early | gate rules 5 and 7 | Rewrite, then template | mutation test (`date_shifted`, `weekday_instead_of_date`) |
| 5 | The model recommends a banned product (Indian labels still list carbofuran, carbosulfan, chlorpyrifos) | gate rule 1 | Rewrite, then template | `test_banned_product_must_be_called_banned`, `banned_added` |
| 6 | The model invents a product or a dose | gate rules 2, 3 and dose | Rewrite, then template | `unknown_added`, `dose_x10` |
| 7 | "Wash it and it's fine", "no need to wait", "mix them" | gate rule 6 | Rewrite, then template | `unsafe_claim` |
| 8 | Someone in crisis asks how much is lethal | `guard.py` first, then the guardrail's SelfHarm topic | The 1166 helpline message, nothing about pesticides; question not stored | `test_crisis_in_three_scripts_and_never_logged`; `CrisisAlarm` |
| 9 | Spraying to make produce look fresh; poisoning fish | `guard.py`, guardrail denied topics | A refusal that says why (and, for freshness, what to do instead) | `test_other_refusals` |
| 10 | A template answer itself fails the gate (a bug in my code) | the gate runs on templates too | A safe default: "ask your AKC, don't harvest before the label waiting period" | `_rules` in `assistant.py`; every eval question checks the gate |
| 11 | A product the table doesn't have (spinosad, emamectin, imidacloprid) | no label row | "I don't have a verified waiting period", no date, no dose | `test_blank_waiting_period_is_unknown_not_zero`, eval d29 |
| 12 | The farmer says "last week" or no date | the date parser returns nothing | The waiting period, and a request for the spray day | eval d26, `test_vague_dates_give_none` |
| 13 | Lambda's clock is UTC; at 1 a.m. in Kathmandu "today" would be yesterday | `config.today_npt()` | Dates counted from Nepal's day | used everywhere `today` defaults |
| 14 | A row in the label table is wrong | **nothing automatic** | A wrong waiting period, stated confidently | Only human review. See below. |
| 15 | A wrong idea with no product, number or known phrase ("sunlight breaks it down fast") | **nothing** | It reaches the farmer | `test_known_gap_unsafe_reasoning_without_product_or_number` pins the gap |
| 16 | The farmer names the wrong pest | nothing | Advice for the pest they named | The answer always ends with the AKC; no photo diagnosis by design (ADR-011) |

## The two that matter most

**#14, a wrong row.** The gate checks the answer against the table, so it cannot catch the table
being wrong. A waiting period of 2 typed for 22 would pass every test. The defences are
procedural: every row carries its source, the subset is small enough to check by hand, the data
ships only through CI (ADR-006), and before real use a second person should check each row
against the PDF. This is the first item in [RESPONSIBLE_AI.md](RESPONSIBLE_AI.md).

**#15, the gate's blind spot.** The gate reads products, numbers, dates and a list of known
unsafe phrases. It does not understand arguments. A test asserts that "Sunlight breaks residue
down quickly." passes today, so that if I close the gap, the test tells me.

## What a bad day looks like

Bedrock is degraded in the APAC profile. Every advice question hits a timeout after 20 seconds and
falls back; the FallbackAlarm fires within the hour. Harvest-date and ban questions are unaffected,
because in hybrid mode they never call Bedrock. Answers stay correct and get plainer; latency is
the cost. Setting the stack parameter `Backend=rules` removes the timeout until Bedrock recovers.
