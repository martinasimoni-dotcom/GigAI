from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4


MANIFEST_NAME = "manifest.json"


@dataclass
class TrashItem:
    item_id: str
    original_path: str
    trashed_path: str
    deleted_at: str
    item_type: str
    reason: str
    exists_in_trash: bool


class TrashManager:
    def __init__(self, workspace_root: Path | None = None, trash_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or _discover_workspace_root()).resolve()
        self.trash_root = (trash_root or (self.workspace_root / "trash")).resolve()
        self.items_root = self.trash_root / "items"
        self.manifest_path = self.trash_root / MANIFEST_NAME

    def move(self, targets: list[str], reason: str = "") -> list[TrashItem]:
        if not targets:
            raise ValueError("At least one target path is required.")

        self._ensure_layout()
        manifest = self._load_manifest()
        moved: list[TrashItem] = []
        batch_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]

        for raw_target in targets:
            source = self._resolve_target(raw_target)
            if not source.exists():
                raise FileNotFoundError(f"Target does not exist: {source}")
            if self._is_inside(source, self.trash_root):
                raise ValueError(f"Target is already inside trash: {source}")
            if not self._is_inside(source, self.workspace_root):
                raise ValueError(f"Target must be inside workspace root: {source}")

            item_id = f"trash_{uuid4().hex[:10]}"
            relative_source = source.relative_to(self.workspace_root)
            destination = self.items_root / batch_id / f"{item_id}_{source.name}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))

            record = TrashItem(
                item_id=item_id,
                original_path=str(relative_source).replace("\\", "/"),
                trashed_path=str(destination.relative_to(self.trash_root)).replace("\\", "/"),
                deleted_at=datetime.now(UTC).isoformat(),
                item_type="directory" if destination.is_dir() else "file",
                reason=reason,
                exists_in_trash=True,
            )
            manifest["items"].append(record.__dict__)
            moved.append(record)

        self._save_manifest(manifest)
        return moved

    def list_items(self) -> list[TrashItem]:
        manifest = self._load_manifest()
        items = [TrashItem(**item) for item in manifest["items"]]
        return list(reversed(items))

    def restore(self, item_id: str, destination: str | None = None) -> TrashItem:
        manifest = self._load_manifest()
        for item in manifest["items"]:
            if item["item_id"] != item_id:
                continue

            trashed_abs = self.trash_root / item["trashed_path"]
            if not trashed_abs.exists():
                raise FileNotFoundError(f"Trashed item no longer exists: {trashed_abs}")

            restore_target = (
                (self.workspace_root / destination).resolve()
                if destination is not None
                else (self.workspace_root / item["original_path"]).resolve()
            )
            if not self._is_inside(restore_target, self.workspace_root):
                raise ValueError(f"Restore target must stay inside workspace root: {restore_target}")
            if restore_target.exists():
                raise FileExistsError(f"Restore target already exists: {restore_target}")

            restore_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trashed_abs), str(restore_target))
            item["exists_in_trash"] = False
            item["restored_at"] = datetime.now(UTC).isoformat()
            item["restored_to"] = str(restore_target.relative_to(self.workspace_root)).replace("\\", "/")
            self._save_manifest(manifest)
            return TrashItem(**{k: item[k] for k in TrashItem.__dataclass_fields__.keys()})

        raise KeyError(f"Trash item not found: {item_id}")

    def _ensure_layout(self) -> None:
        self.items_root.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self._save_manifest({"items": []})

    def _resolve_target(self, raw_target: str) -> Path:
        candidate = Path(raw_target)
        if candidate.is_absolute():
            return candidate.resolve()
        if candidate.exists():
            return candidate.resolve()
        return (self.workspace_root / candidate).resolve()

    def _load_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"items": []}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        self.trash_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    @staticmethod
    def _is_inside(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Move unwanted files into a local recoverable trash folder.")
    sub = parser.add_subparsers(dest="command", required=True)

    move_parser = sub.add_parser("move", help="Move files or folders into ./trash.")
    move_parser.add_argument("targets", nargs="+", help="File or folder paths relative to the workspace.")
    move_parser.add_argument("--reason", default="", help="Optional reason recorded in the trash manifest.")

    list_parser = sub.add_parser("list", help="List trashed items.")
    list_parser.add_argument("--limit", type=int, default=20, help="Maximum number of items to print.")

    restore_parser = sub.add_parser("restore", help="Restore an item from trash.")
    restore_parser.add_argument("item_id", help="Trash item ID from the list command.")
    restore_parser.add_argument("--to", dest="destination", help="Optional new destination inside the workspace.")

    return parser


def _discover_workspace_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here.parent, *here.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    manager = TrashManager()

    if args.command == "move":
        moved = manager.move(args.targets, reason=args.reason)
        _print_json(
            {
                "status": "moved",
                "trash_root": str(manager.trash_root),
                "items": [item.__dict__ for item in moved],
            }
        )
        return

    if args.command == "list":
        items = manager.list_items()[: max(0, args.limit)]
        _print_json(
            {
                "trash_root": str(manager.trash_root),
                "items": [item.__dict__ for item in items],
            }
        )
        return

    if args.command == "restore":
        restored = manager.restore(args.item_id, destination=args.destination)
        _print_json(
            {
                "status": "restored",
                "item": restored.__dict__,
            }
        )
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
