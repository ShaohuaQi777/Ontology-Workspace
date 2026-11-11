"""Scoped CONFIGURED source registry. No connection execution or secret resolution."""
import time,uuid
from sqlalchemy import text
from ontology_platform.domain.connections import ConnectionView,TargetRegistry
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.infrastructure.connection_schema import initialize_connection_schema
from ontology_platform.semantic.dto import reject_credential_authority


class ConnectionService:
    def __init__(self,store,accounts,targets):
        if type(targets) is not TargetRegistry: raise ValueError('Operator targets required')
        self.store=store; self.accounts=accounts; self.targets=targets

    def initialize(self): initialize_connection_schema(self.store)

    def _target(self,project_id,name,alias):
        try:
            if type(name) is not str or not 1<=len(name)<=200 or type(alias) is not str:
                raise ValueError('Invalid connection')
            reject_credential_authority(name)
        except Exception: raise ServiceError('INVALID_CONNECTION') from None
        return self.targets.resolve(alias,project_id)

    def _view(self,row,project_id):
        target=self.targets.resolve(row['target_alias'],project_id)
        if target.binding_hash!=row['target_hash']: raise ServiceError('TARGET_CHANGED')
        return ConnectionView(row['connection_id'],project_id,row['name'],row['target_alias'],row['kind'],row['id'])

    def _row(self,connection,project_id,connection_id):
        row=connection.execute(text('SELECT r.* FROM connections c JOIN connection_revisions r ON c.current_revision=r.id WHERE c.id=:id AND c.project_id=:project'),{'id':connection_id,'project':project_id}).mappings().first()
        if row is None: raise ServiceError('CONNECTION_NOT_FOUND')
        return row

    def create(self,actor,project_id,name,target_alias):
        self.accounts.require_project(actor,project_id,'edit')
        target=self._target(project_id,name,target_alias)
        connection_id=str(uuid.uuid4()); revision=str(uuid.uuid4())
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,'edit')
            target=self._target(project_id,name,target_alias)
            connection.execute(text('INSERT INTO connections(id,project_id,current_revision) VALUES(:id,:project,:revision)'),{'id':connection_id,'project':project_id,'revision':revision})
            self._save(connection,actor,connection_id,revision,None,name,target)
            self.accounts._audit(connection,actor.user_id,'create_connection',connection_id,'succeeded')
        return ConnectionView(connection_id,project_id,name,target_alias,target.kind,revision)

    def _save(self,connection,actor,connection_id,revision,parent,name,target):
        connection.execute(text('INSERT INTO connection_revisions(id,connection_id,parent_revision,name,target_alias,kind,target_hash,actor_id,created_at) VALUES(:id,:connection,:parent,:name,:alias,:kind,:hash,:actor,:created)'),{'id':revision,'connection':connection_id,'parent':parent,'name':name,'alias':target.alias,'kind':target.kind,'hash':target.binding_hash,'actor':actor.user_id,'created':int(time.time())})

    def update(self,actor,project_id,connection_id,base_revision,name,target_alias):
        self.accounts.require_project(actor,project_id,'edit')
        target=self._target(project_id,name,target_alias)
        revision=str(uuid.uuid4())
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,'edit')
            target=self._target(project_id,name,target_alias)
            old=self._row(connection,project_id,connection_id)
            if old['id']!=base_revision: raise ServiceError('STALE_REVISION')
            self._save(connection,actor,connection_id,revision,old['id'],name,target)
            changed=connection.execute(text('UPDATE connections SET current_revision=:revision WHERE id=:id AND project_id=:project AND current_revision=:base'),{'revision':revision,'id':connection_id,'project':project_id,'base':base_revision})
            if changed.rowcount!=1: raise ServiceError('STALE_REVISION')
            self.accounts._audit(connection,actor.user_id,'update_connection',connection_id,'succeeded')
        return ConnectionView(connection_id,project_id,name,target_alias,target.kind,revision)

    def get(self,actor,project_id,connection_id):
        self.accounts.require_project(actor,project_id,'read')
        with self.store.transaction() as connection:
            return self._view(self._row(connection,project_id,connection_id),project_id)

    def list(self,actor,project_id):
        self.accounts.require_project(actor,project_id,'read')
        with self.store.transaction() as connection:
            rows=connection.execute(text('SELECT r.* FROM connections c JOIN connection_revisions r ON c.current_revision=r.id WHERE c.project_id=:project ORDER BY c.id'),{'project':project_id}).mappings().all()
            return [self._view(row,project_id) for row in rows]
