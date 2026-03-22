"""
Setup the PostgreSQL database with pgvector extension and all tables.
Run: python scripts/setup_database.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

from models.database import init_db, engine
from sqlalchemy import text

print("🔧 Setting up GIGAI database...")

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection OK")
except Exception as e:
    print(f"❌ Cannot connect to database: {e}")
    print("   Make sure Docker is running: docker-compose up -d")
    sys.exit(1)

try:
    init_db()
    print("✅ Tables created (proposals, decisions)")
    print("✅ pgvector extension enabled")
    print("\n🎉 Database ready! Next: cd backend && python main.py")
except Exception as e:
    print(f"❌ Setup error: {e}")
    sys.exit(1)
