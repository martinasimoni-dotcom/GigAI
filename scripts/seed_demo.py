"""
scripts/seed_demo.py

Seeds the knowledge_chunks table with realistic data for the GigAI demo scenario:
  - Past material change records (aluminum -> wood window substitutions)
  - Supplier contacts and pricing
  - Project specifications
  - Historical outcomes for confidence scoring

Run once before the demo:
    python -m scripts.seed_demo

Idempotent: checks for existing demo data before inserting.
"""
import logging
import sys
from pathlib import Path

# Make sure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


DEMO_CHUNKS = [
    # --- Past material change records ---
    {
        "text": (
            "Material Change Order #MC-2024-087: Aluminum window frames substituted with wood frames "
            "on floors 2-4, Barcelona Tower project. 18 units. Approved by PM Sarah Chen and "
            "Owner Representative Robert Hayes. FSC-certified wood sourced from Premium Wood Co. "
            "Lead time: 6 weeks. Cost delta: +$2,100 vs aluminum. Installation completed on schedule. "
            "Structural assessment confirmed by Lisa Wong — no load-bearing impact."
        ),
        "source": "historical_changes",
        "metadata": {
            "outcome": "approved",
            "success_rate": 0.95,
            "project": "barcelona_tower",
            "change_type": "material_substitution",
            "element": "window",
            "material_original": "aluminum",
            "material_new": "wood",
            "quantity": 18,
            "lead_time_weeks": 6,
        },
    },
    {
        "text": (
            "Material Change Order #MC-2023-042: Steel door frames substituted with aluminum frames "
            "on ground floor, Diagonal Mar project. 8 units. Approved by PM. "
            "Cost savings: $4,200. Lead time: 4 weeks. No structural issues."
        ),
        "source": "historical_changes",
        "metadata": {
            "outcome": "approved",
            "success_rate": 0.90,
            "project": "diagonal_mar",
            "change_type": "material_substitution",
            "element": "door",
            "quantity": 8,
        },
    },
    {
        "text": (
            "Material Change Order #MC-2024-031: Vinyl window frames proposed for exterior use "
            "on floors 5-7, Gracia Heights project. 24 units. REJECTED — vinyl not approved "
            "for exterior use above 3rd floor per project specifications. PM escalated to "
            "architect for alternative proposal. Delay: 2 weeks."
        ),
        "source": "historical_changes",
        "metadata": {
            "outcome": "rejected",
            "success_rate": 0.0,
            "project": "gracia_heights",
            "change_type": "material_substitution",
            "element": "window",
            "material_new": "vinyl",
            "quantity": 24,
            "rejection_reason": "vinyl not approved above floor 3 exterior",
        },
    },
    {
        "text": (
            "Material Change Order #MC-2025-011: Aluminum window frames substituted with wood frames "
            "3rd floor, Sant Gervasi Tower project. 10 units. Approved. "
            "FSC certified timber from Premium Wood Co. (contact: Jane Miller, j.miller@premiumwood.es). "
            "Lead time: 5 weeks. Cost: $8,500 total. Structural weight assessment passed."
        ),
        "source": "historical_changes",
        "metadata": {
            "outcome": "approved",
            "success_rate": 0.92,
            "project": "sant_gervasi_tower",
            "change_type": "material_substitution",
            "element": "window",
            "material_original": "aluminum",
            "material_new": "wood",
            "quantity": 10,
            "lead_time_weeks": 5,
            "supplier": "Premium Wood Co.",
        },
    },

    # --- Supplier data ---
    {
        "text": (
            "Supplier: Premium Wood Co. "
            "Contact: Jane Miller — j.miller@premiumwood.es — +34 93 412 5500. "
            "Products: FSC-certified hardwood and softwood window frames, door frames, cladding. "
            "Lead time: 4-6 weeks depending on quantity. "
            "Pricing: Wood window frames €750-€950 per unit depending on dimensions. "
            "FSC certification documentation provided on request. "
            "Approved supplier for Barcelona Tower project. Past performance: excellent."
        ),
        "source": "supplier_database",
        "metadata": {
            "supplier": "Premium Wood Co.",
            "contact": "Jane Miller",
            "email": "j.miller@premiumwood.es",
            "phone": "+34 93 412 5500",
            "product_type": "wood_frames",
            "fsc_certified": True,
            "approved_projects": ["barcelona_tower", "sant_gervasi_tower"],
        },
    },
    {
        "text": (
            "Supplier: Euroframe S.L. "
            "Contact: Marco Vidal — m.vidal@euroframe.es — +34 93 220 3410. "
            "Products: Aluminum window and curtain wall systems. "
            "Lead time: 8-14 weeks (currently extended due to supply chain issues). "
            "Pricing: Aluminum window frames €600-€800 per unit. "
            "Note: As of March 2026, 14-week backlog on all standard profiles."
        ),
        "source": "supplier_database",
        "metadata": {
            "supplier": "Euroframe S.L.",
            "contact": "Marco Vidal",
            "email": "m.vidal@euroframe.es",
            "product_type": "aluminum_frames",
            "current_lead_time_weeks": 14,
            "backlog_note": "Extended backlog as of March 2026",
        },
    },

    # --- Project specifications ---
    {
        "text": (
            "Barcelona Tower Project Specification — Section 08 52 00: Wood Windows. "
            "All wood window frames must be FSC certified (Forest Stewardship Council). "
            "Species: European oak or equivalent. Finish: factory-primed, site-painted. "
            "Thermal performance: U-value ≤ 1.4 W/m²K. "
            "Structural: weight per unit not to exceed 45 kg. "
            "Installation: per manufacturer instructions, bed in low-modulus silicone sealant."
        ),
        "source": "project_specifications",
        "metadata": {
            "spec_section": "08 52 00",
            "element": "window",
            "material": "wood",
            "project": "barcelona_tower",
            "fsc_required": True,
            "max_weight_kg": 45,
        },
    },
    {
        "text": (
            "Barcelona Tower Project Specification — Section 08 51 13: Aluminum Windows. "
            "Aluminum window frames: thermally broken extruded aluminum 6063-T5. "
            "Finish: powder-coated RAL 7016. "
            "Thermal performance: U-value ≤ 1.2 W/m²K. "
            "Weight per unit: 28-32 kg. "
            "Current supplier: Euroframe S.L. — experiencing 14-week lead time delays."
        ),
        "source": "project_specifications",
        "metadata": {
            "spec_section": "08 51 13",
            "element": "window",
            "material": "aluminum",
            "project": "barcelona_tower",
            "current_supplier": "Euroframe S.L.",
        },
    },
    {
        "text": (
            "Barcelona Tower Project — Floor 3 Window Schedule (Drawing A-301). "
            "Total window units on 3rd floor: 12. "
            "Types: W-03A (1200x1800mm) x 8 units, W-03B (900x1500mm) x 4 units. "
            "Current spec: aluminum frames per Section 08 51 13. "
            "Installation zone: exterior facade, south and west elevations. "
            "Scheduled installation: Week 14 (April 7-11, 2026)."
        ),
        "source": "acc_floor_plans",
        "metadata": {
            "drawing": "A-301",
            "floor": 3,
            "element": "window",
            "quantity": 12,
            "project": "barcelona_tower",
            "installation_week": 14,
        },
    },

    # --- Policy knowledge ---
    {
        "text": (
            "GigAI Policy Reminder: Wood frame window substitutions exceeding 8 units "
            "require a structural weight assessment before PO issuance (RULE-008). "
            "Wood frames weigh approximately 38-45 kg per unit vs aluminum at 28-32 kg. "
            "Structural engineer must confirm the 3rd floor slab can accommodate the additional load. "
            "Lisa Wong (l.wong@structeng.es) is the assigned structural engineer for Barcelona Tower."
        ),
        "source": "policy_knowledge",
        "metadata": {
            "rule": "RULE-008",
            "element": "window",
            "material": "wood",
            "threshold_quantity": 8,
        },
    },
    {
        "text": (
            "GigAI Policy: All wood materials on Barcelona Tower must carry FSC certification. "
            "RULE-017: Require FSC certification documentation from supplier before PO issuance. "
            "Premium Wood Co. provides FSC Chain of Custody certificate on all orders. "
            "Request certificate number from Jane Miller when placing order."
        ),
        "source": "policy_knowledge",
        "metadata": {
            "rule": "RULE-017",
            "material_category": "wood",
            "fsc_required": True,
        },
    },
]


def seed():
    from src.shared.db.vector_store import embed_and_store
    from src.shared.db.postgres import get_connection, release_connection

    # Check if demo data already exists
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM knowledge_chunks WHERE source IN %s",
                (("historical_changes", "supplier_database", "project_specifications",
                  "acc_floor_plans", "policy_knowledge"),),
            )
            count = cur.fetchone()["count"]
    finally:
        release_connection(conn)

    if count >= len(DEMO_CHUNKS):
        logger.info("Demo data already seeded (%d chunks found). Skipping.", count)
        return

    logger.info("Seeding %d knowledge chunks in one batch...", len(DEMO_CHUNKS))

    from src.shared.llm.voyage import embed_batch
    from src.shared.db.postgres import get_connection, release_connection
    import json
    from psycopg2.extras import execute_values

    texts = [c["text"] for c in DEMO_CHUNKS]
    embeddings = embed_batch(texts, input_type="document")

    conn = get_connection()
    try:
        rows = [
            (c["text"], emb, c["source"], json.dumps(c["metadata"]))
            for c, emb in zip(DEMO_CHUNKS, embeddings)
        ]
        with conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO knowledge_chunks (content, embedding, source, metadata) VALUES %s",
                rows,
            )
        conn.commit()
    finally:
        release_connection(conn)

    logger.info("Done. %d chunks seeded into knowledge_chunks.", len(DEMO_CHUNKS))


if __name__ == "__main__":
    seed()
