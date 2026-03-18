from pathlib import Path

from gigai.trash_manager import TrashManager


def test_move_file_into_trash_and_list(scratch_dir: Path) -> None:
    source = scratch_dir / "sample.txt"
    source.write_text("keep me recoverable", encoding="utf-8")

    manager = TrashManager(workspace_root=scratch_dir)
    moved = manager.move(["sample.txt"], reason="cleanup")
    items = manager.list_items()

    assert len(moved) == 1
    assert moved[0].original_path == "sample.txt"
    assert moved[0].reason == "cleanup"
    assert not source.exists()
    assert (scratch_dir / "trash" / moved[0].trashed_path).exists()
    assert items[0].item_id == moved[0].item_id


def test_restore_file_from_trash(scratch_dir: Path) -> None:
    source = scratch_dir / "nested" / "draft.txt"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("draft", encoding="utf-8")

    manager = TrashManager(workspace_root=scratch_dir)
    moved = manager.move(["nested/draft.txt"])
    restored = manager.restore(moved[0].item_id)

    restored_path = scratch_dir / "nested" / "draft.txt"
    assert restored.item_id == moved[0].item_id
    assert restored_path.exists()
    assert restored_path.read_text(encoding="utf-8") == "draft"


def test_reject_moving_trash_folder_itself(scratch_dir: Path) -> None:
    trash_root = scratch_dir / "trash"
    trash_root.mkdir(parents=True, exist_ok=True)
    inside = trash_root / "already.txt"
    inside.write_text("ignore", encoding="utf-8")

    manager = TrashManager(workspace_root=scratch_dir)

    try:
        manager.move([str(inside)])
    except ValueError as ex:
        assert "already inside trash" in str(ex)
    else:
        raise AssertionError("Expected move() to reject targets inside trash.")
