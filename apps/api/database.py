import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from .models import Base

def make_engine(url):
    options = {"connect_args": {"check_same_thread": False, "timeout": 30}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, **options)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def configure(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    return engine

def initialize(engine):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            for table in Base.metadata.sorted_tables:
                connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
            connection.execute(text("""CREATE OR REPLACE FUNCTION relay_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'append-only record'; END; $$"""))
            for name in ("audit_events", "credit_transactions", "worker_earnings"):
                connection.execute(text(f'DROP TRIGGER IF EXISTS immutable ON {name}'))
                connection.execute(text(f'CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION relay_immutable()'))
        else:
            for name in ("audit_events", "credit_transactions", "worker_earnings"):
                for action in ("UPDATE", "DELETE"):
                    connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {name}_{action} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT, 'append-only record'); END"))

@contextmanager
def transaction(engine):
    with Session(engine, expire_on_commit=False) as session:
        try:
            if engine.dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            else:
                session.execute(text("SELECT pg_advisory_xact_lock(728194103)"))
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
