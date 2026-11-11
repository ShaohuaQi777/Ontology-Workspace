"""Durable local queue metadata; no native SDK objects or transient credentials."""
from sqlalchemy import text


def initialize_job_schema(store):
    with store.transaction() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), actor_id TEXT NOT NULL REFERENCES accounts(id), session_digest TEXT NOT NULL, operation TEXT NOT NULL, request_json TEXT NOT NULL, bindings_json TEXT NOT NULL, workspace_revision TEXT NOT NULL, idempotency_key TEXT NOT NULL, input_hash TEXT NOT NULL, run_id TEXT NOT NULL UNIQUE, replay_of TEXT REFERENCES jobs(id), state TEXT NOT NULL CHECK(state IN ('pending','running','succeeded','failed','cancelled','interrupted')), attempt INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0, worker_id TEXT, heartbeat INTEGER, result_json TEXT, error_code TEXT, created_at INTEGER NOT NULL, UNIQUE(project_id,actor_id,idempotency_key))"))
        connection.execute(text('CREATE TABLE IF NOT EXISTS job_events(id INTEGER PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), state TEXT NOT NULL, created_at INTEGER NOT NULL)'))
