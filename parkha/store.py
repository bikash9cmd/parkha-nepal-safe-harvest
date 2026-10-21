"""The answer log: one DynamoDB item per answer, redacted, expiring after 30 days.

It is how a bad answer gets found (thumbs down, gate failures, fallbacks) and how the
evaluation set grows from real questions. Crisis questions are never stored.
"""

from __future__ import annotations

import time
import uuid

from . import guard

TTL_DAYS = 30


def record(table, question: str, reply) -> str:
    answer_id = uuid.uuid4().hex
    item = {
        "answer_id": answer_id,
        "ts": int(time.time()),
        "expires_at": int(time.time()) + TTL_DAYS * 86400,
        "backend": reply.backend,
        "language": reply.language,
        "refusal": reply.refusal or "",
        "fallback": reply.fallback or "",
        "rewrites": reply.rewrites,
        "input_tokens": reply.input_tokens,
        "output_tokens": reply.output_tokens,
    }
    if reply.log_question:
        item["question"] = guard.redact(question)[:500]
        item["answer"] = guard.redact(reply.answer)[:2000]
    table.put_item(Item=item)
    return answer_id


def feedback(table, answer_id: str, helpful: bool, note: str = "") -> None:
    table.update_item(
        Key={"answer_id": answer_id},
        UpdateExpression="SET helpful = :h, feedback_note = :n",
        ConditionExpression="attribute_exists(answer_id)",
        ExpressionAttributeValues={":h": helpful, ":n": guard.redact(note)[:300]},
    )
