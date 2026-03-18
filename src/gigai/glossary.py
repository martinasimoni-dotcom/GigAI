from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from functools import lru_cache


DEFAULT_GLOSSARY_PATH = "config/project_glossary.json"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass
class ProjectGlossary:
    term_normalization: dict[str, str] = field(default_factory=dict)
    space_aliases: dict[str, list[str]] = field(default_factory=dict)

    def aliases_for(self, space_name: str) -> list[str]:
        return self.space_aliases.get(_normalize_key(space_name), [])


@lru_cache(maxsize=16)
def _load_glossary_cached(glossary_path: str) -> ProjectGlossary:
    path = Path(glossary_path)
    if not path.exists():
        return ProjectGlossary()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ProjectGlossary()

    raw_terms = data.get("term_normalization", {})
    term_normalization: dict[str, str] = {}
    if isinstance(raw_terms, dict):
        for k, v in raw_terms.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                term_normalization[_normalize_key(k)] = _normalize_key(v)

    raw_aliases = data.get("space_aliases", {})
    space_aliases: dict[str, list[str]] = {}
    if isinstance(raw_aliases, dict):
        for canonical, aliases in raw_aliases.items():
            if not isinstance(canonical, str) or not canonical.strip():
                continue
            if not isinstance(aliases, list):
                continue
            clean_aliases: list[str] = []
            for alias in aliases:
                if isinstance(alias, str) and alias.strip():
                    clean_aliases.append(alias.strip())
            if clean_aliases:
                space_aliases[_normalize_key(canonical)] = clean_aliases

    return ProjectGlossary(
        term_normalization=term_normalization,
        space_aliases=space_aliases,
    )


def get_project_glossary(glossary_path: str | None = None) -> ProjectGlossary:
    resolved_path = glossary_path or os.getenv("GIGAI_PROJECT_GLOSSARY", DEFAULT_GLOSSARY_PATH)
    return _load_glossary_cached(str(Path(resolved_path)))
