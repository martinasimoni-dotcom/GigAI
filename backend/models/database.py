from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

try:
    from pgvector.sqlalchemy import Vector
    VECTOR_ENABLED = True
except ImportError:
    VECTOR_ENABLED = False

from config import settings

Base = declarative_base()


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text)
    status = Column(String, default="pending")  # pending | approved | rejected
    confidence = Column(Float)
    cost = Column(Float)
    actions = Column(JSON)
    extracted = Column(JSON)       # raw haiku extraction
    proposal_data = Column(JSON)   # full sonnet output

    # RFI workflow fields
    source_rfi_id = Column(String, nullable=True)        # originating ACC RFI id
    acc_project_id = Column(String, nullable=True)       # ACC project id
    assigned_user_email = Column(String, nullable=True)  # email of RFI assignee
    email_sent = Column(Boolean, default=False)          # auto-email dispatched
    email_sent_at = Column(DateTime, nullable=True)      # when it was sent

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    if VECTOR_ENABLED:
        embedding = Column(Vector(1024), nullable=True)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    proposal_id = Column(String, nullable=False)
    decision = Column(String, nullable=False)  # approved | rejected
    reason = Column(Text)
    decided_by = Column(String, default="user")
    decided_at = Column(DateTime, default=datetime.utcnow)
    if VECTOR_ENABLED:
        embedding = Column(Vector(1024), nullable=True)


engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    if VECTOR_ENABLED:
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.create_all(engine)

    # Add new columns to existing tables (safe no-op if already present)
    _migrate_proposals_table()


def _migrate_proposals_table():
    """Add RFI workflow columns to the proposals table if they don't exist yet."""
    new_columns = {
        "source_rfi_id": "VARCHAR",
        "acc_project_id": "VARCHAR",
        "assigned_user_email": "VARCHAR",
        "email_sent": "BOOLEAN DEFAULT FALSE",
        "email_sent_at": "TIMESTAMP",
    }
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("proposals")}
        for col_name, col_type in new_columns.items():
            if col_name not in existing:
                conn.execute(text(f'ALTER TABLE proposals ADD COLUMN {col_name} {col_type}'))
                print(f"  ↳ Added column: proposals.{col_name}")
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
