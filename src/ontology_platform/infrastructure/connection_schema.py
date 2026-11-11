"""Immutable source connection revisions and project-scoped current pointers."""
from sqlalchemy import text


def initialize_connection_schema(store):
    with store.transaction() as connection:
        connection.execute(text('CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(id),current_revision TEXT NOT NULL)'))
        connection.execute(text('CREATE TABLE IF NOT EXISTS connection_revisions(id TEXT PRIMARY KEY,connection_id TEXT NOT NULL REFERENCES connections(id),parent_revision TEXT REFERENCES connection_revisions(id),name TEXT NOT NULL,target_alias TEXT NOT NULL,kind TEXT NOT NULL,target_hash TEXT NOT NULL,actor_id TEXT NOT NULL REFERENCES accounts(id),created_at INTEGER NOT NULL)'))
