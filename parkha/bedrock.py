"""The Bedrock backend: Amazon Nova Lite through the Converse API, with tool use.

One BedrockSession is one question. The model sees the system prompt, the question and four
tool specs; it calls tools, gets their dicts back, and writes the answer. If the gate rejects the
answer, the same session is asked once to rewrite it, with the reasons.

The guardrail is applied once, to the question, with ApplyGuardrail, not attached to every
Converse call; the output side is the gate's job, which is stricter about what matters here
(products, waiting periods, dates) and costs nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

from . import config, tools
from .corpus import Corpus
from .labels import LabelBook


class TooManyToolRounds(RuntimeError):
    pass


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    def add(self, usage: dict) -> None:
        self.input_tokens += int(usage.get("inputTokens", 0))
        self.output_tokens += int(usage.get("outputTokens", 0))
        self.calls += 1


def apply_guardrail(client, guardrail_id: str, version: str, question: str) -> str | None:
    """The guardrail's blocked message if it intervenes on the question, else None."""
    resp = client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=version,
        source="INPUT",
        content=[{"text": {"text": question}}],
    )
    if resp.get("action") == "GUARDRAIL_INTERVENED":
        outputs = resp.get("outputs") or [{}]
        return outputs[0].get("text") or "I can only answer questions about crop pests and safe pesticide use."
    return None


@dataclass
class BedrockSession:
    client: object
    corpus: Corpus
    book: LabelBook
    today: date
    system: str
    model_id: str = config.MODEL_ID
    messages: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    def _request(self) -> dict:
        return {
            "modelId": self.model_id,
            "system": [{"text": self.system}],
            "messages": self.messages,
            "toolConfig": tools.bedrock_tool_config(),
            "inferenceConfig": {"maxTokens": config.MAX_OUTPUT_TOKENS, "temperature": 0.0},
            "additionalModelRequestFields": {"inferenceConfig": {"topK": 1}},
        }

    def say(self, text: str) -> str:
        self.messages.append({"role": "user", "content": [{"text": text}]})
        for _ in range(config.MAX_TOOL_ROUNDS + 1):
            resp = self.client.converse(**self._request())
            self.usage.add(resp.get("usage", {}))
            msg = resp["output"]["message"]
            self.messages.append(msg)
            if resp.get("stopReason") != "tool_use":
                return "".join(b.get("text", "") for b in msg.get("content", [])).strip()
            results = []
            for block in msg["content"]:
                use = block.get("toolUse")
                if not use:
                    continue
                out = tools.call(self.corpus, self.book, self.today, use["name"], use.get("input") or {})
                out = json.loads(json.dumps(out, default=str))
                self.tool_calls.append((use["name"], use.get("input") or {}))
                self.tool_results.append(out)
                results.append({"toolResult": {"toolUseId": use["toolUseId"], "content": [{"json": out}]}})
            self.messages.append({"role": "user", "content": results})
        raise TooManyToolRounds(f"no answer after {config.MAX_TOOL_ROUNDS} tool rounds")


def client(region: str = config.BEDROCK_REGION):
    import boto3
    from botocore.config import Config

    # Fail fast: the rules backend can answer in milliseconds if Bedrock is slow.
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(connect_timeout=3, read_timeout=20, retries={"max_attempts": 2, "mode": "standard"}),
    )
