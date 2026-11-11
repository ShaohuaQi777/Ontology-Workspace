"""Actual private SQLite files; no mocked transaction or persistence evidence."""
import importlib,os,stat
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def new(path):
    return importlib.import_module('ontology_platform.infrastructure.metadata').MetadataStore('sqlite:///'+str(path))


def test_rows_survive_close_and_reopen(tmp_path):
    path=tmp_path/'metadata.db'; store=new(path); store.initialize()
    with store.transaction() as connection:
        connection.execute(text('CREATE TABLE technical_items(id INTEGER PRIMARY KEY, value TEXT NOT NULL)'))
        connection.execute(text("INSERT INTO technical_items VALUES(1,'persisted')"))
    store.close()
    store=new(path); store.initialize()
    with store.transaction() as connection:
        assert connection.execute(text('SELECT value FROM technical_items WHERE id=1')).scalar_one()=='persisted'
    store.close()
    assert stat.S_IMODE(path.stat().st_mode)==0o600


def test_failed_transaction_does_not_commit_partial_write(tmp_path):
    store=new(tmp_path/'metadata.db'); store.initialize()
    with store.transaction() as connection: connection.execute(text('CREATE TABLE technical_items(id INTEGER PRIMARY KEY)'))
    with pytest.raises(RuntimeError):
        with store.transaction() as connection:
            connection.execute(text('INSERT INTO technical_items VALUES(1)'))
            raise RuntimeError('controlled rollback')
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM technical_items')).scalar_one()==0
    store.close()


def test_foreign_keys_enforced_on_actual_connections(tmp_path):
    store=new(tmp_path/'metadata.db'); store.initialize()
    with store.transaction() as connection:
        connection.execute(text('CREATE TABLE parent(id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE child(parent_id INTEGER REFERENCES parent(id))'))
        assert connection.execute(text('PRAGMA busy_timeout')).scalar_one()==5000
    with pytest.raises(IntegrityError):
        with store.transaction() as connection: connection.execute(text('INSERT INTO child VALUES(99)'))
    store.close()


def test_future_schema_rejected_without_destroying_existing_data(tmp_path):
    path=tmp_path/'metadata.db'; store=new(path); store.initialize()
    with store.transaction() as connection: connection.execute(text('UPDATE app_schema SET version=999'))
    store.close(); store=new(path)
    with pytest.raises(Exception) as caught: store.initialize()
    assert getattr(caught.value,'code',None)=='UNSUPPORTED_SCHEMA'
    store.close()
    import sqlite3
    with sqlite3.connect(path) as connection: assert connection.execute('SELECT version FROM app_schema').fetchone()[0]==999


@pytest.mark.parametrize('url',['sqlite:///:memory:','sqlite:///relative.db','postgresql://alice:TECHNICAL-CREDENTIAL-MARKER@example.invalid/database'])
def test_unsupported_or_unsafe_urls_rejected_without_secret_echo(url):
    with pytest.raises(ValueError) as caught: importlib.import_module('ontology_platform.infrastructure.metadata').MetadataStore(url)
    assert 'TECHNICAL-CREDENTIAL-MARKER' not in str(caught.value)


def test_db_symlink_not_followed(tmp_path):
    real=tmp_path/'owned.db'; real.write_bytes(b'unchanged')
    link=tmp_path/'metadata.db'; link.symlink_to(real)
    with pytest.raises(ValueError): new(link)
    assert real.read_bytes()==b'unchanged'


def test_directory_symlink_and_public_parent_rejected(tmp_path):
    owned=tmp_path/'owned'; owned.mkdir(mode=0o700)
    link=tmp_path/'alias'; link.symlink_to(owned,target_is_directory=True)
    with pytest.raises(ValueError): new(link/'metadata.db')
    public=tmp_path/'public'; public.mkdir(mode=0o755)
    with pytest.raises(ValueError): new(public/'metadata.db')
    assert not (owned/'metadata.db').exists() and not (public/'metadata.db').exists()


def test_non_database_regular_file_not_replaced(tmp_path):
    path=tmp_path/'metadata.db'; path.write_bytes(b'technical non-database file'); os.chmod(path,0o600)
    store=new(path)
    with pytest.raises(Exception): store.initialize()
    store.close(); assert path.read_bytes()==b'technical non-database file'
