"""Private server-owned SQLite metadata. This is containment, not an OS sandbox."""
from contextlib import contextmanager
import os,stat
from pathlib import Path
from sqlalchemy import create_engine,event,text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from ontology_platform.domain.service_errors import ServiceError


class MetadataStore:
    def __init__(self,url:str):
        try: parsed=make_url(url)
        except Exception: raise ValueError('Unsupported metadata location') from None
        path=Path(parsed.database or '')
        if (parsed.drivername!='sqlite' or parsed.username or parsed.password or parsed.host or parsed.port
                or parsed.query or not path.is_absolute() or '..' in path.parts or str(path)==':memory:'):
            raise ValueError('Unsupported metadata location')
        for component in (*reversed(path.parents),path):
            if component.is_symlink(): raise ValueError('Metadata symlinks are not allowed')
        if not path.parent.is_dir() or stat.S_IMODE(path.parent.stat().st_mode)&0o077:
            raise ValueError('Private metadata parent directory required')
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            os.close(fd)
        except FileExistsError:
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)&0o077:
                raise ValueError('Private regular metadata file required') from None
        except OSError: raise ValueError('Metadata location is unavailable') from None
        self._engine=create_engine(parsed,connect_args={'check_same_thread':False})
        self._ready=False

        @event.listens_for(self._engine,'connect')
        def configure(connection,record):
            cursor=connection.cursor()
            try:
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.execute('PRAGMA busy_timeout=5000')
            finally: cursor.close()

    def initialize(self)->None:
        self._ready=False
        try:
            with self._engine.begin() as connection:
                connection.execute(text('CREATE TABLE IF NOT EXISTS app_schema(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)'))
                rows=connection.execute(text('SELECT id,version FROM app_schema LIMIT 2')).all()
                if rows and rows!=[(1,1)]: raise ServiceError('UNSUPPORTED_SCHEMA')
                if not rows: connection.execute(text('INSERT INTO app_schema VALUES(1,1)'))
        except SQLAlchemyError: raise ServiceError('STORAGE_UNAVAILABLE') from None
        self._ready=True

    @contextmanager
    def transaction(self):
        if not self._ready: raise ServiceError('NOT_INITIALIZED')
        with self._engine.begin() as connection: yield connection

    def close(self)->None:
        self._ready=False
        self._engine.dispose()
