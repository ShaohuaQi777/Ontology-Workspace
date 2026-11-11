"""Immutable workspace content/source metadata, not semantic modeling logic."""
from sqlalchemy import text

STATEMENTS=(
    'CREATE TABLE IF NOT EXISTS revisions(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), layer TEXT NOT NULL, parent_revision TEXT NOT NULL, content_json TEXT NOT NULL, dependencies_json TEXT NOT NULL, sha256 TEXT NOT NULL, created_at INTEGER NOT NULL)',
    'CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), format TEXT NOT NULL, revision TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, filename TEXT NOT NULL, created_at INTEGER NOT NULL)',
    'CREATE TABLE IF NOT EXISTS certification_records(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), revision_id TEXT NOT NULL REFERENCES revisions(id), actor_id TEXT NOT NULL REFERENCES accounts(id), dependencies_json TEXT NOT NULL, evidence_sha256 TEXT NOT NULL, evidence_json TEXT NOT NULL, created_at INTEGER NOT NULL)',
)


def initialize_workspace_schema(store):
    with store.transaction() as connection:
        for statement in STATEMENTS: connection.execute(text(statement))
