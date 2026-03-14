#!/usr/bin/env python3
"""
Retrieval Quality Validation Script -- GigAI Knowledge Folder
Tests 20+ semantic search queries against the seeded pgvector knowledge folder.

Usage: python scripts/test_retrieval_quality.py
       python scripts/test_retrieval_quality.py --dry-run

Prerequisites:
  - .env file with VOYAGE_API_KEY and DATABASE_URL
  - Knowledge folder seeded: python scripts/seed_knowledge_folder.py

Success threshold: 18/20 queries (90% recall).

This is a development-time validation tool, NOT a pytest test.
It lives in scripts/ to avoid accidental collection by pytest.
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path for src.* imports when run as standalone script
sys.path.insert(0, str(Path(__file__).parent.parent))

# MUST load env before any src.* imports -- config.settings singleton triggers at import time
from dotenv import load_dotenv
load_dotenv()

# Note: src.shared.db.vector_store transitively imports config.settings singleton.
# It is imported lazily inside run_validation() so --dry-run works without real credentials.
# load_dotenv() above ensures env vars are ready before the lazy import happens at call time.


QUERIES = [
    # -----------------------------------------------------------------
    # Team directory queries (expected_source: "knowledge_folder/team_directory")
    # 4 queries covering supplier names, roles, contacts
    # -----------------------------------------------------------------
    {
        "query": "wood frame supplier pricing contact",
        "expected_source": "knowledge_folder/team_directory",
        "label": "Wood supplier contact",
    },
    {
        "query": "who is responsible for procurement approval",
        "expected_source": "knowledge_folder/team_directory",
        "label": "Procurement lead",
    },
    {
        "query": "project manager contact for material changes",
        "expected_source": "knowledge_folder/team_directory",
        "label": "PM contact",
    },
    {
        "query": "aluminum window supplier lead time",
        "expected_source": "knowledge_folder/team_directory",
        "label": "Aluminum supplier",
    },

    # -----------------------------------------------------------------
    # Rules file queries (expected_source: "knowledge_folder/rules")
    # 5 queries covering approval thresholds, escalation, material change requirements
    # -----------------------------------------------------------------
    {
        "query": "material change approval threshold cost limit",
        "expected_source": "knowledge_folder/rules",
        "label": "Cost threshold rule",
    },
    {
        "query": "when is escalation required for procurement",
        "expected_source": "knowledge_folder/rules",
        "label": "Escalation rule",
    },
    {
        "query": "structural review required for window replacement",
        "expected_source": "knowledge_folder/rules",
        "label": "Structural review rule",
    },
    {
        "query": "quantity threshold requiring procurement task",
        "expected_source": "knowledge_folder/rules",
        "label": "Quantity rule",
    },
    {
        "query": "drawing markup required for material substitution",
        "expected_source": "knowledge_folder/rules",
        "label": "Drawing markup rule",
    },

    # -----------------------------------------------------------------
    # Historical patterns queries (expected_source: "knowledge_folder/historical_patterns")
    # 6 queries covering past aluminum/wood changes, accepted precedents, quantities
    # -----------------------------------------------------------------
    {
        "query": "past aluminum to wood window change approved",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "Aluminum-wood precedent",
    },
    {
        "query": "previous material substitution 3rd floor accepted",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "3rd floor precedent",
    },
    {
        "query": "EVT-012 window change 12 units structural review",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "EVT-012 direct precedent",
    },
    {
        "query": "similar change cost outcome approved",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "Cost outcome history",
    },
    {
        "query": "material change success rate historical",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "Success rate",
    },
    {
        "query": "window substitution precedent schedule impact",
        "expected_source": "knowledge_folder/historical_patterns",
        "label": "Schedule impact history",
    },

    # -----------------------------------------------------------------
    # Glossary queries (expected_source: "knowledge_folder/glossary")
    # 5 queries covering element types, materials, locations, unit IDs
    # -----------------------------------------------------------------
    {
        "query": "what is W-301 unit type",
        "expected_source": "knowledge_folder/glossary",
        "label": "Unit ID definition",
    },
    {
        "query": "aluminum frame window element type",
        "expected_source": "knowledge_folder/glossary",
        "label": "Aluminum frame definition",
    },
    {
        "query": "3rd floor location zone building plan",
        "expected_source": "knowledge_folder/glossary",
        "label": "3rd floor zone",
    },
    {
        "query": "wood frame material specification",
        "expected_source": "knowledge_folder/glossary",
        "label": "Wood frame definition",
    },
    {
        "query": "drawing A-301 floor plan reference",
        "expected_source": "knowledge_folder/glossary",
        "label": "Drawing reference",
    },
]


def run_validation() -> int:
    """
    Run all 20+ queries against the seeded pgvector knowledge folder.

    Prints per-query PASS/FAIL status.
    Reports overall recall score.
    Exits 1 if recall < 90%, exits 0 if recall >= 90%.

    Returns:
        0 if recall >= 90%, 1 if recall < 90%.
    """
    # Lazy import -- vector_store transitively loads config.settings singleton;
    # importing here (not at module level) keeps --dry-run working without DB creds.
    from src.shared.db.vector_store import search  # noqa: PLC0415

    passed = 0
    failed = []

    print(f"Running {len(QUERIES)} retrieval quality queries...")
    print("-" * 60)

    for item in QUERIES:
        try:
            results = search(item["query"], top_k=1, input_type="query")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR [{item['label']}] search() raised: {exc}")
            failed.append(item["label"])
            continue

        # Use startswith() matching -- seed script may append /chunk_N suffixes
        if results and results[0].get("source", "").startswith(item["expected_source"]):
            passed += 1
            status = "PASS"
        else:
            failed.append(item["label"])
            status = "FAIL"
            actual = results[0].get("source", "no results") if results else "no results"
            print(
                f"  FAIL [{item['label']}]"
                f" expected={item['expected_source']}"
                f" got={actual}"
            )

    total = len(QUERIES)
    recall = passed / total if total > 0 else 0.0

    print("-" * 60)
    print(f"\nRecall: {passed}/{total} = {recall:.1%}")

    if failed:
        print(f"Failed queries ({len(failed)}): {', '.join(failed)}")

    threshold = 0.90
    if recall < threshold:
        print(f"\nBELOW THRESHOLD: {recall:.1%} < {threshold:.0%}")
        print("Action required: re-seed knowledge folder or review query/source mapping.")
        return 1
    else:
        print(f"\nPASS: recall >= {threshold:.0%}")
        return 0


def main() -> int:
    """Entry point. Handles --dry-run flag."""
    if "--dry-run" in sys.argv:
        print(f"DRY RUN: {len(QUERIES)} queries defined. Real run requires seeded pgvector DB.")
        print(f"Query categories:")
        categories = {}
        for q in QUERIES:
            cat = q["expected_source"].split("/")[-1]
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} queries")
        return 0

    return run_validation()


if __name__ == "__main__":
    sys.exit(main())
