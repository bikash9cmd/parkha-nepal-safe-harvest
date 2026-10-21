"""Command line: python -m parkha ask "..." [--debug] [--today YYYY-MM-DD] | python -m parkha serve"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date

from . import assistant, config


def main() -> None:
    p = argparse.ArgumentParser(prog="parkha")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--debug", action="store_true", help="print tool calls, results and gate problems")
    a.add_argument("--today", help="pretend today is this date (YYYY-MM-DD)")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("parkha.api:app", host="127.0.0.1", port=args.port)
        return
    settings = config.Settings.from_env()
    today = date.fromisoformat(args.today) if args.today else None
    guardrail = (settings.guardrail_id, settings.guardrail_version) if settings.guardrail_id else None
    reply = assistant.ask(
        args.question, backend=os.environ.get("PARKHA_BACKEND", "rules"), today=today, guardrail=guardrail
    )
    print(reply.answer)
    if args.debug:
        print(json.dumps(reply.public(debug=True), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
