from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pytest


@pytest.fixture
def scratch_dir() -> Path:
    root = Path(".pytest_runtime")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"run_{uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, scratch_dir: Path) -> None:
    monkeypatch.setenv("GIGAI_DB_PATH", str(scratch_dir / "gigai.sqlite3"))
