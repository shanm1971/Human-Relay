import pytest
from sqlalchemy import text

def test_postgres_rls_blocks_unprivileged_reader(client,setup):
    engine=client.app.state.engine
    if engine.dialect.name!="postgresql":pytest.skip("PostgreSQL RLS requires PostgreSQL")
    with engine.begin() as c:
        c.execute(text("SET LOCAL ROLE pg_read_all_data"))
        assert c.scalar(text("SELECT count(*) FROM agents"))==0
        assert c.scalar(text("SELECT count(*) FROM workers"))==0
        assert c.scalar(text("SELECT count(*) FROM credit_transactions"))==0
        assert c.scalar(text("SELECT count(*) FROM audit_events"))==0
