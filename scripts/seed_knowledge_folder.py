"""
Seed script: chunk knowledge folder files, embed via Voyage-3, store in pgvector.
KF-05

Run from repo root: python scripts/seed_knowledge_folder.py
"""
import json
import logging
import os
import re
import sys
from pathlib import Path

# Ensure repo root is on sys.path for src.* imports when run as standalone script
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from psycopg2.extras import execute_values

from src.shared.db.postgres import get_connection, release_connection
from src.shared.llm.voyage import embed_batch

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

SOURCES = {
    "glossary": str(REPO_ROOT / "knowledge_folder/glossary/demo_project.md"),
    "team": str(REPO_ROOT / "knowledge_folder/team_directory/demo_project.json"),
    "rules": str(REPO_ROOT / "knowledge_folder/rules/demo_project.yaml"),
    "history": str(REPO_ROOT / "knowledge_folder/historical_patterns/demo_project.json"),
}

SOURCE_KEYS = list(SOURCES.values())  # used for idempotency DELETE


def chunk_markdown_by_sections(text: str) -> list[tuple[str, str]]:
    """
    Split markdown on ## headings. Returns list of (heading, full_section_text) tuples.
    Skips content before the first ## heading. Empty/whitespace input returns [].
    """
    if not text or not text.strip():
        return []
    pattern = r"(?m)^(?=## )"
    parts = re.split(pattern, text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part or not part.startswith("## "):
            continue
        lines = part.splitlines()
        heading = lines[0].lstrip("#").strip() if lines else "unknown"
        chunks.append((heading, part))
    return chunks


def chunk_team_directory(path: str) -> list[tuple[dict, str]]:
    """
    One chunk per team member. Returns list of (metadata_dict, text_for_embedding).
    Text is human-readable prose (not raw JSON) for better embedding quality.
    """
    with open(path, encoding="utf-8") as f:
        members = json.load(f)
    chunks = []
    for member in members:
        text = (
            f"Name: {member['name']}\n"
            f"Role: {member['role']}\n"
            f"Email: {member['email']}\n"
            f"Phone: {member['phone']}\n"
            f"Responsibilities: {', '.join(member['responsibilities'])}\n"
            f"Area of Authority: {member['area_of_authority']}"
        )
        meta = {
            "type": "team_member",
            "name": member["name"],
            "role": member["role"],
            "project": "harbor_view_tower",
        }
        chunks.append((meta, text))
    return chunks


def chunk_rules(path: str) -> list[tuple[dict, str]]:
    """
    One chunk per rule entry. Returns list of (metadata_dict, text_for_embedding).
    Handles both bare list YAML and top-level 'rules:' key.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", data) if isinstance(data, dict) else data
    chunks = []
    for rule in rules:
        text = (
            f"Rule ID: {rule['rule_id']}\n"
            f"Description: {rule['description']}\n"
            f"Condition: {rule['condition']}\n"
            f"Action: {rule['action']}\n"
            f"Stakeholders: {', '.join(rule.get('stakeholders', []))}\n"
            f"Priority: {rule.get('priority', 'normal')}"
        )
        meta = {
            "type": "rule",
            "rule_id": rule["rule_id"],
            "priority": rule.get("priority", "normal"),
            "project": "harbor_view_tower",
        }
        chunks.append((meta, text))
    return chunks


def chunk_historical_patterns(path: str) -> list[tuple[dict, str]]:
    """
    One chunk per historical event. Returns list of (metadata_dict, text_for_embedding).
    Includes material and decision fields in metadata for future filtering (CTX-02).
    """
    with open(path, encoding="utf-8") as f:
        events = json.load(f)
    chunks = []
    for event in events:
        text = (
            f"Event ID: {event['event_id']}\n"
            f"Date: {event['date']}\n"
            f"Element Type: {event['element_type']}\n"
            f"Material Change: {event['material_original']} → {event['material_new']}\n"
            f"Location: {event['location']}\n"
            f"Quantity: {event['quantity']}\n"
            f"Reason: {event['reason']}\n"
            f"Outcome: {event['outcome']}\n"
            f"Cost Impact: ${event['cost_impact']:,}\n"
            f"Schedule Impact: {event['schedule_impact_days']} days\n"
            f"PM Decision: {event['pm_decision']}\n"
            f"Lessons Learned: {event['lessons_learned']}"
        )
        meta = {
            "type": "historical_event",
            "event_id": event["event_id"],
            "material_original": event["material_original"],
            "material_new": event["material_new"],
            "element_type": event["element_type"],
            "pm_decision": event["pm_decision"],
            "project": "harbor_view_tower",
        }
        chunks.append((meta, text))
    return chunks


def seed() -> dict:
    """
    Load, chunk, embed, and store all knowledge folder files.

    Strategy: collect ALL (text, meta, source) tuples first, then call
    embed_batch() ONCE for all ~45 chunks, then bulk-INSERT with per-row
    metadata via execute_values. Single Voyage-3 API call. One DB transaction.

    Returns dict with chunk counts per file and total.
    """
    # --- 1. Collect all chunks ---
    all_texts: list[str] = []
    all_metas: list[dict] = []
    all_sources: list[str] = []
    counts: dict = {}

    # Glossary: chunk by ## section
    glossary_chunks = chunk_markdown_by_sections(
        Path(SOURCES["glossary"]).read_text(encoding="utf-8")
    )
    for heading, section_text in glossary_chunks:
        all_texts.append(section_text)
        all_metas.append({
            "type": "glossary",
            "section": heading,
            "project": "harbor_view_tower",
            "file": "demo_project.md",
        })
        all_sources.append(SOURCES["glossary"])
    counts["glossary"] = len(glossary_chunks)

    # Team directory: one chunk per member
    team_chunks = chunk_team_directory(SOURCES["team"])
    for meta, text in team_chunks:
        all_texts.append(text)
        all_metas.append(meta)
        all_sources.append(SOURCES["team"])
    counts["team"] = len(team_chunks)

    # Rules: one chunk per rule
    rules_chunks = chunk_rules(SOURCES["rules"])
    for meta, text in rules_chunks:
        all_texts.append(text)
        all_metas.append(meta)
        all_sources.append(SOURCES["rules"])
    counts["rules"] = len(rules_chunks)

    # Historical patterns: one chunk per event
    history_chunks = chunk_historical_patterns(SOURCES["history"])
    for meta, text in history_chunks:
        all_texts.append(text)
        all_metas.append(meta)
        all_sources.append(SOURCES["history"])
    counts["history"] = len(history_chunks)

    total = len(all_texts)
    logger.info(f"Collected {total} chunks: {counts}")

    # --- 2. Idempotency DELETE ---
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM knowledge_chunks WHERE source = ANY(%s)",
                (SOURCE_KEYS,),
            )
            deleted = cur.rowcount
        conn.commit()
        logger.info(f"Deleted {deleted} existing chunks (idempotency)")
    finally:
        release_connection(conn)

    # --- 3. Single embed_batch call (all texts < 128 limit) ---
    logger.info(f"Embedding {total} chunks via Voyage-3 (single batch)...")
    embeddings = embed_batch(all_texts, input_type="document")
    logger.info(f"Embeddings received: {len(embeddings)} vectors @ 1024 dimensions")

    # --- 4. Bulk INSERT with per-row metadata ---
    conn = get_connection()
    try:
        rows = [
            (text, emb, src, json.dumps(meta))
            for text, emb, src, meta in zip(all_texts, embeddings, all_sources, all_metas)
        ]
        with conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO knowledge_chunks (content, embedding, source, metadata) VALUES %s",
                rows,
            )
        conn.commit()
        logger.info(f"Inserted {len(rows)} chunks into knowledge_chunks")
    finally:
        release_connection(conn)

    counts["total"] = total
    print(f"\nSeed complete: {counts}")
    return counts


if __name__ == "__main__":
    seed()
