"""One-command, non-trading UKACTIVE-A5 prospective shadow runner."""

from __future__ import annotations

import argparse
import json
import sys

from ukactive_a5_shadow_core import LATEST_REPORT_MD, WARNING, run_operational_mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen UKACTIVE A5 shadow comparison; this program cannot place an order."
    )
    parser.add_argument(
        "--mode",
        choices=["setup", "signal", "execute", "telemetry", "report", "auto"],
        default="auto",
        help="Permitted state-machine action (default: auto).",
    )
    parser.add_argument(
        "--asof",
        default="latest",
        help="Latest fully validated cutoff or a YYYY-MM-DD historical as-of date.",
    )
    parser.add_argument(
        "--commit-push",
        action="store_true",
        help="Commit and push only when new prospective evidence was recorded.",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print the machine-readable run summary after the Markdown report.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "setup" and args.commit_push:
        raise SystemExit("Setup may not create a prospective Git evidence commit; commit the freeze separately.")
    try:
        payload = run_operational_mode(args.mode, args.asof, commit_push=args.commit_push)
    except Exception as error:  # Operational failures must be unmistakable.
        print("UKACTIVE A5 OPERATIONAL FAILURE", file=sys.stderr)
        print(str(error), file=sys.stderr)
        print(WARNING, file=sys.stderr)
        return 1
    if LATEST_REPORT_MD.exists():
        print(LATEST_REPORT_MD.read_text(encoding="utf-8"))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    if args.json_summary:
        print("\n--- MACHINE-READABLE RUN SUMMARY ---")
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
