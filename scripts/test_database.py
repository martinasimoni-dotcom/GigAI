"""
Test database connection and table setup.
Run: python scripts/test_database.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

print("🧪 Testing Database Connection...")

try:
    from models.database import engine, SessionLocal, Proposal, Decision

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ PostgreSQL: {version[:30]}...")

    # Test pgvector
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT '[1,2,3]'::vector"))
        print("✅ pgvector extension: available")
    except Exception:
        print("⚠️  pgvector not enabled — run setup_database.py")

    # Test table query
    db = SessionLocal()
    try:
        count = db.query(Proposal).count()
        decisions = db.query(Decision).count()
        print(f"✅ Proposals table: {count} records")
        print(f"✅ Decisions table: {decisions} records")
    finally:
        db.close()

    print("\n🎉 Database is healthy!")

except Exception as e:
    print(f"❌ Database error: {e}")
    print("   Make sure Docker is running: docker-compose up -d")
    print("   Then run: python scripts/setup_database.py")
    sys.exit(1)
