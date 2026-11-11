"""Local account/session/project ACL schema, extending metadata version one."""
from sqlalchemy import text

STATEMENTS=(
    'CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash BLOB NOT NULL, salt BLOB NOT NULL, global_role TEXT NOT NULL CHECK(global_role IN (\'admin\',\'member\')), disabled INTEGER NOT NULL DEFAULT 0 CHECK(disabled IN (0,1)))',
    'CREATE TABLE IF NOT EXISTS account_bootstrap(id INTEGER PRIMARY KEY CHECK(id=1))',
    'CREATE TABLE IF NOT EXISTS sessions(digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES accounts(id), expires_at INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)))',
    'CREATE TABLE IF NOT EXISTS login_failures(subject TEXT PRIMARY KEY, window_start INTEGER NOT NULL, attempts INTEGER NOT NULL)',
    'CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, namespace TEXT NOT NULL UNIQUE, owner_id TEXT NOT NULL REFERENCES accounts(id), workspace_revision TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS memberships(user_id TEXT NOT NULL REFERENCES accounts(id), project_id TEXT NOT NULL REFERENCES projects(id), role TEXT NOT NULL CHECK(role IN (\'engineer\',\'consultant\',\'expert\',\'admin\',\'owner\')), PRIMARY KEY(user_id,project_id,role))',
    'CREATE TABLE IF NOT EXISTS permission_denies(user_id TEXT NOT NULL REFERENCES accounts(id), project_id TEXT NOT NULL REFERENCES projects(id), action TEXT NOT NULL, PRIMARY KEY(user_id,project_id,action))',
    'CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY, actor_id TEXT, action TEXT NOT NULL, resource_id TEXT, outcome TEXT NOT NULL, created_at INTEGER NOT NULL)',
)


def initialize_account_schema(store):
    with store.transaction() as connection:
        for statement in STATEMENTS: connection.execute(text(statement))
