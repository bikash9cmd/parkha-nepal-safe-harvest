"""Lambda handler for the HTTP API (payload format 2.0): POST /ask, POST /feedback, GET /health.

The clients are created once per container. The label book and notes ship inside the package:
a change to the ban list is a deploy, and a deploy runs the evaluation in CI first. That is
the point; see ADR-006 in docs/ALTERNATIVES.md.
"""

from __future__ import annotations

import json
import logging
import os

from .. import assistant, config, store

log = logging.getLogger()
log.setLevel(logging.INFO)

_settings = config.Settings.from_env()
_bedrock = None
_table = None


def _clients():
    global _bedrock, _table
    if _settings.backend == "bedrock" and _bedrock is None:
        from .. import bedrock

        _bedrock = bedrock.client(_settings.region)
    if _settings.log_table and _table is None:
        import boto3

        _table = boto3.resource("dynamodb").Table(_settings.log_table)
    return _bedrock, _table


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _metrics(reply) -> None:
    # CloudWatch embedded metric format: one line, no PutMetricData call, no dimensions (cost).
    print(
        json.dumps(
            {
                "_aws": {
                    "Timestamp": 0,
                    "CloudWatchMetrics": [
                        {
                            "Namespace": "Parkha",
                            "Dimensions": [[]],
                            "Metrics": [
                                {"Name": n, "Unit": u}
                                for n, u in [
                                    ("Answers", "Count"),
                                    ("Fallbacks", "Count"),
                                    ("GateRejections", "Count"),
                                    ("CrisisRefusals", "Count"),
                                    ("InputTokens", "Count"),
                                    ("OutputTokens", "Count"),
                                    ("LatencyMs", "Milliseconds"),
                                ]
                            ],
                        }
                    ],
                },
                "Answers": 1,
                "Fallbacks": int(bool(reply.fallback)),
                "GateRejections": len(reply.gate_problems),
                "CrisisRefusals": int(reply.refusal == "crisis"),
                "InputTokens": reply.input_tokens,
                "OutputTokens": reply.output_tokens,
                "LatencyMs": reply.latency_ms,
            }
        ).replace('"Timestamp": 0', f'"Timestamp": {int(__import__("time").time() * 1000)}')
    )


def api(event, context):
    route = event.get("routeKey", "")
    if route == "GET /health":
        return _resp(200, {"ok": True, "backend": _settings.backend, "version": os.environ.get("PARKHA_VERSION", "")})
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "body must be JSON"})
    client, table = _clients()
    if route == "POST /ask":
        q = body.get("question")
        if not isinstance(q, str) or not q.strip():
            return _resp(400, {"error": "question is required"})
        guardrail = (_settings.guardrail_id, _settings.guardrail_version) if _settings.guardrail_id else None
        reply = assistant.ask(
            q[:2000], backend=_settings.backend, client=client, model_id=_settings.model_id, guardrail=guardrail
        )
        _metrics(reply)
        out = reply.public()
        if table is not None:
            out["answer_id"] = store.record(table, q, reply)
        return _resp(200, out)
    if route == "POST /feedback":
        if table is None or not isinstance(body.get("answer_id"), str) or not isinstance(body.get("helpful"), bool):
            return _resp(400, {"error": "answer_id (string) and helpful (boolean) are required"})
        try:
            store.feedback(table, body["answer_id"], body["helpful"], str(body.get("note", "")))
        except table.meta.client.exceptions.ConditionalCheckFailedException:
            return _resp(404, {"error": "unknown answer_id"})
        return _resp(200, {"ok": True})
    return _resp(404, {"error": "not found"})
