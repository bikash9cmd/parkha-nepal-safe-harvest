"""FastAPI app for local runs. aws/handlers.py serves the same routes on Lambda."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from . import __version__, assistant, config

app = FastAPI(title="Parkha", version=__version__)
settings = config.Settings.from_env()


class Ask(BaseModel):
    question: str = Field(max_length=2000)
    debug: bool = False


@app.get("/health")
def health() -> dict:
    return {"ok": True, "backend": settings.backend, "today": config.today_npt().isoformat()}


@app.post("/ask")
def ask(body: Ask) -> dict:
    guardrail = (settings.guardrail_id, settings.guardrail_version) if settings.guardrail_id else None
    reply = assistant.ask(body.question, backend=settings.backend, model_id=settings.model_id, guardrail=guardrail)
    return reply.public(debug=body.debug)
