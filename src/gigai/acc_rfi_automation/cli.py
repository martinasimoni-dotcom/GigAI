from __future__ import annotations

import argparse
import time

from .config import AccRfiAutomationConfig
from .service import RfiAutomationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only ACC RFI email/calendar automation.")
    parser.add_argument("--project-id", required=True, help="ACC project identifier.")
    parser.add_argument("--rfis-input", help="Offline JSON file for RFI responses.")
    parser.add_argument("--watch", action="store_true", help="Continuously poll ACC RFIs.")
    parser.add_argument("--interval-seconds", type=int, default=300, help="Polling interval for --watch mode.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = AccRfiAutomationConfig.from_env(
        project_id=args.project_id,
        rfis_input_path=args.rfis_input,
        poll_interval_seconds=args.interval_seconds,
    )
    service = RfiAutomationService(config)

    if args.watch:
        while True:
            service.run_once()
            time.sleep(config.poll_interval_seconds)

    service.run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

