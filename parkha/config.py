"""Constants and environment-driven settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CORPUS_DIR = ROOT / "corpus"

# A question longer than this is not a farming question; it is usually a pasted document or an attack.
MAX_QUESTION_CHARS = 500

# Bedrock. Amazon Nova Lite through the APAC cross-region profile, served from Mumbai (closest to Nepal).
BEDROCK_REGION = "ap-south-1"
MODEL_ID = "apac.amazon.nova-lite-v1:0"
MAX_TOOL_ROUNDS = 4
MAX_OUTPUT_TOKENS = 600
MAX_REWRITES = 1

# How many advisory notes the model sees per search.
TOP_K_NOTES = 3

# Land units used in Nepal, in square metres. Label rates are per hectare; nobody farms in hectares here.
ROPANI_M2 = 508.72  # hills
KATTHA_M2 = 338.63  # Terai
HECTARE_M2 = 10_000.0

CRISIS_LINE = "1166"

NPT = timedelta(hours=5, minutes=45)


def today_npt() -> date:
    """Today's date in Nepal. Lambda runs in UTC, and 'today' at 2 a.m. in Kathmandu is still yesterday there."""
    return (datetime.now(UTC) + NPT).date()


@dataclass(frozen=True)
class Settings:
    backend: str
    model_id: str
    region: str
    guardrail_id: str | None
    guardrail_version: str | None
    log_table: str | None

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            backend=os.environ.get("PARKHA_BACKEND", "rules"),  # rules | bedrock | hybrid
            model_id=os.environ.get("PARKHA_MODEL_ID", MODEL_ID),
            region=os.environ.get("PARKHA_BEDROCK_REGION", BEDROCK_REGION),
            guardrail_id=os.environ.get("PARKHA_GUARDRAIL_ID") or None,
            guardrail_version=os.environ.get("PARKHA_GUARDRAIL_VERSION") or None,
            log_table=os.environ.get("PARKHA_LOG_TABLE") or None,
        )
