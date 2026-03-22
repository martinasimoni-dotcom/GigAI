from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from pathlib import Path

from .auth import AccessTokenProvider
from .client import AccReadonlyClient
from .config import AccReadonlySyncConfig
from .models import SnapshotMetadata, SnapshotPayload, utc_now_iso
from .normalize import normalize_issue_records, normalize_rfi_records
from .storage import append_log, read_state, write_snapshot, write_state

log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only ACC issues/RFIs extractor for local Revit sync.")
    parser.add_argument("--project-id", required=True, help="ACC project identifier.")
    parser.add_argument("--output", help="Path to write the normalized snapshot JSON.")
    parser.add_argument("--include-rfis", action="store_true", help="Fetch RFIs in addition to issues.")
    parser.add_argument("--issues-input", help="Offline JSON file for issue responses.")
    parser.add_argument("--rfis-input", help="Offline JSON file for RFI responses.")
    parser.add_argument("--watch", action="store_true", help="Continuously poll ACC and refresh the snapshot.")
    parser.add_argument("--interval-seconds", type=int, default=300, help="Polling interval for --watch mode.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = AccReadonlySyncConfig.from_env(
        project_id=args.project_id,
        include_rfis=bool(args.include_rfis),
        output_path=args.output,
        issues_input_path=args.issues_input,
        rfis_input_path=args.rfis_input,
    )
    interval_seconds = max(args.interval_seconds, 5)

    if args.watch:
        while True:
            try:
                _run_once(config)
            except Exception as ex:
                append_log(config.log_path, f"[{utc_now_iso()}] watch -> error -> {ex}")
                log.error(f"Error in watch loop: {ex}")
            time.sleep(interval_seconds)

    _run_once(config)
    return 0


def _run_once(config: AccReadonlySyncConfig) -> None:
    access_token = ""
    if config.issues_input_path is None or (config.include_rfis and config.rfis_input_path is None):
        access_token = AccessTokenProvider(config).get()

    client = AccReadonlyClient(config, access_token)
    issue_payload = client.fetch_issues()
    issue_items, issue_ignored = normalize_issue_records(issue_payload.records)

    rfi_items = []
    rfi_ignored = 0
    sources = [issue_payload.source]
    if config.include_rfis:
        rfi_payload = client.fetch_rfis()
        rfi_items, rfi_ignored = normalize_rfi_records(rfi_payload.records)
        sources.append(rfi_payload.source)

    all_items = sorted(issue_items + rfi_items, key=lambda item: (item.type, item.id))
    previous_state = read_state(config.state_path)
    current_state: dict[str, str] = {}
    new_items = 0
    updated_items = 0
    generated_at = utc_now_iso()

    for item in all_items:
        key = f"{item.type}:{item.id}"
        digest = _compute_item_digest(item.to_dict())
        current_state[key] = digest
        previous_digest = previous_state.get(key)
        if previous_digest is None:
            new_items += 1
            append_log(config.log_path, f"[{generated_at}] {key} -> detected -> new")
        elif previous_digest != digest:
            updated_items += 1
            append_log(config.log_path, f"[{generated_at}] {key} -> detected -> updated")

    payload = SnapshotPayload(
        metadata=SnapshotMetadata(
            generatedAt=generated_at,
            projectId=config.project_id,
            itemsWritten=len(all_items),
            ignoredWithoutLocation=issue_ignored + rfi_ignored,
            newItems=new_items,
            updatedItems=updated_items,
            sources=sources,
        ),
        items=all_items,
    )
    write_snapshot(config.output_path, payload)
    write_state(config.state_path, current_state)
    append_log(
        config.log_path,
        f"[{payload.metadata.generatedAt}] project={config.project_id} "
        f"items_written={payload.metadata.itemsWritten} ignored={payload.metadata.ignoredWithoutLocation} "
        f"new={payload.metadata.newItems} updated={payload.metadata.updatedItems}",
    )


def _compute_item_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
