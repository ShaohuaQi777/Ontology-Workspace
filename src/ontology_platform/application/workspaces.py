"""Scoped immutable governance metadata; semantic modeling remains in Semantica."""
from dataclasses import dataclass
import hashlib,json,time,uuid
from urllib.parse import urlsplit
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.semantic.dto import reject_credential_authority
from ontology_platform.infrastructure.workspace_schema import initialize_workspace_schema
from ontology_platform.infrastructure.source_policy import checked_json,check_source
from ontology_platform.infrastructure.source_store import SourceStore

LAYERS={'tbox','abox','shacl','rules','vocabulary'}


@dataclass(frozen=True)
class Project:
    project_id:str
    name:str
    namespace:str
    workspace_revision:str


@dataclass(frozen=True)
class Revision:
    revision_id:str
    project_id:str
    layer:str
    content:dict
    dependencies:dict
    sha256:str
    state:str='DRAFT'


@dataclass(frozen=True)
class SourceSnapshot:
    source_id:str
    project_id:str
    format:str
    revision:str
    sha256:str
    size:int


@dataclass(frozen=True)
class CertificationRecord:
    record_id:str
    revision_id:str
    evidence_sha256:str
    evidence:dict


class WorkspaceService:
    def __init__(self,store,accounts,artifact_root,clock=time.time):
        self.store=store; self.accounts=accounts; self.clock=clock
        self.sources=SourceStore(artifact_root,store.database_path)

    def initialize(self): initialize_workspace_schema(self.store)

    def create_project(self,actor,name,namespace):
        try:
            if type(name) is not str or not 1<=len(name)<=200 or type(namespace) is not str or not 1<=len(namespace)<=2048:
                raise ValueError('Invalid project')
            reject_credential_authority(name); reject_credential_authority(namespace)
            if not urlsplit(namespace).scheme or any(ch.isspace() for ch in namespace): raise ValueError('Absolute namespace required')
        except Exception: raise ServiceError('INVALID_WORKSPACE') from None
        project_id=str(uuid.uuid4())
        try:
            with self.store.transaction() as connection:
                user=self.accounts._actor(connection,actor)
                connection.execute(text('INSERT INTO projects(id,name,namespace,owner_id,workspace_revision) VALUES(:id,:name,:namespace,:owner,\'w0\')'),{'id':project_id,'name':name,'namespace':namespace,'owner':user['id']})
                connection.execute(text('INSERT INTO memberships(user_id,project_id,role) VALUES(:user,:project,\'owner\')'),{'user':user['id'],'project':project_id})
                self.accounts._audit(connection,user['id'],'create_project',project_id,'succeeded')
        except IntegrityError: raise ServiceError('NAMESPACE_CONFLICT') from None
        return Project(project_id,name,namespace,'w0')

    def save_layer(self,actor,project_id,layer,base_revision,content,dependencies):
        self.accounts.require_project(actor,project_id,'edit')
        try:
            if layer not in LAYERS or type(content) is not dict or type(dependencies) is not dict or not set(dependencies)<=LAYERS:
                raise ValueError('Invalid layer')
            content=checked_json(content); dependencies=checked_json(dependencies)
            if not all(type(value) is str for value in dependencies.values()): raise ValueError('Invalid dependencies')
            canonical=json.dumps({'content':content,'dependencies':dependencies},sort_keys=True,separators=(',',':'),ensure_ascii=False)
        except Exception: raise ServiceError('INVALID_WORKSPACE') from None
        revision_id=str(uuid.uuid4()); sha256=hashlib.sha256(canonical.encode()).hexdigest()
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,'edit')
            current=connection.execute(text('SELECT workspace_revision FROM projects WHERE id=:id'),{'id':project_id}).scalar_one()
            if current!=base_revision: raise ServiceError('STALE_REVISION')
            for dep_layer,dep_revision in dependencies.items():
                row=connection.execute(text('SELECT layer FROM revisions WHERE id=:revision AND project_id=:project'),{'revision':dep_revision,'project':project_id}).scalar()
                if row!=dep_layer: raise ServiceError('INVALID_DEPENDENCY')
            connection.execute(text('INSERT INTO revisions(id,project_id,layer,parent_revision,content_json,dependencies_json,sha256,created_at) VALUES(:id,:project,:layer,:parent,:content,:deps,:sha,:time)'),{'id':revision_id,'project':project_id,'layer':layer,'parent':base_revision,'content':json.dumps(content,ensure_ascii=False,separators=(',',':')),'deps':json.dumps(dependencies,sort_keys=True,separators=(',',':')),'sha':sha256,'time':int(self.clock())})
            updated=connection.execute(text('UPDATE projects SET workspace_revision=:revision WHERE id=:project AND workspace_revision=:base'),{'revision':revision_id,'project':project_id,'base':base_revision})
            if updated.rowcount!=1: raise ServiceError('STALE_REVISION')
            self.accounts._audit(connection,actor.user_id,'save_layer',revision_id,'succeeded')
        return Revision(revision_id,project_id,layer,content,dependencies,sha256)

    def read_revision(self,actor,project_id,revision_id):
        self.accounts.require_project(actor,project_id,'read')
        with self.store.transaction() as connection:
            # Keep all certification/dependency checks on one actual SQLite snapshot.
            connection.exec_driver_sql('BEGIN')
            row=connection.execute(text('SELECT * FROM revisions WHERE id=:id AND project_id=:project'),{'id':revision_id,'project':project_id}).mappings().first()
            certified=connection.execute(text('SELECT 1 FROM certification_records WHERE revision_id=:id AND project_id=:project LIMIT 1'),{'id':revision_id,'project':project_id}).first()
            if row is not None and certified:
                required={**json.loads(row['dependencies_json']),row['layer']:revision_id}
                for layer,expected in required.items():
                    latest=connection.execute(text('SELECT id FROM revisions WHERE project_id=:project AND layer=:layer ORDER BY rowid DESC LIMIT 1'),{'project':project_id,'layer':layer}).scalar()
                    if latest!=expected: certified=None; break
        if row is None: raise ServiceError('INVALID_DEPENDENCY')
        return Revision(row['id'],row['project_id'],row['layer'],json.loads(row['content_json']),json.loads(row['dependencies_json']),row['sha256'],'CERTIFIED' if certified else 'DRAFT')

    def record_certification(self,actor,project_id,revision_id,evidence):
        self.accounts.require_project(actor,project_id,'certify')
        try:
            if type(evidence) is not dict or not evidence: raise ValueError('Evidence required')
            evidence=checked_json(evidence)
            canonical=json.dumps(evidence,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        except Exception: raise ServiceError('INVALID_WORKSPACE') from None
        record_id=str(uuid.uuid4()); evidence_sha=hashlib.sha256(canonical.encode()).hexdigest()
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,'certify')
            row=connection.execute(text('SELECT * FROM revisions WHERE id=:id AND project_id=:project'),{'id':revision_id,'project':project_id}).mappings().first()
            if row is None: raise ServiceError('INVALID_DEPENDENCY')
            latest=connection.execute(text('SELECT id FROM revisions WHERE project_id=:project AND layer=:layer ORDER BY rowid DESC LIMIT 1'),{'project':project_id,'layer':row['layer']}).scalar()
            if latest!=revision_id: raise ServiceError('STALE_REVISION')
            for layer,dependency in json.loads(row['dependencies_json']).items():
                current=connection.execute(text('SELECT id FROM revisions WHERE project_id=:project AND layer=:layer ORDER BY rowid DESC LIMIT 1'),{'project':project_id,'layer':layer}).scalar()
                if current!=dependency: raise ServiceError('STALE_REVISION')
            connection.execute(text('INSERT INTO certification_records(id,project_id,revision_id,actor_id,dependencies_json,evidence_sha256,evidence_json,created_at) VALUES(:id,:project,:revision,:actor,:deps,:evidence,:evidence_json,:time)'),{'id':record_id,'project':project_id,'revision':revision_id,'actor':actor.user_id,'deps':row['dependencies_json'],'evidence':evidence_sha,'evidence_json':canonical,'time':int(self.clock())})
            self.accounts._audit(connection,actor.user_id,'certify_revision',revision_id,'succeeded')
        return CertificationRecord(record_id,revision_id,evidence_sha,evidence)

    def register_source(self,actor,project_id,format,data):
        self.accounts.require_project(actor,project_id,'edit')
        try: check_source(format,data)
        except Exception: raise ServiceError('INVALID_SOURCE') from None
        source_id=str(uuid.uuid4()); revision=str(uuid.uuid4()); sha256=hashlib.sha256(data).hexdigest()
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,'edit')
            try: filename=self.sources.write(project_id,source_id,format,data)
            except Exception: raise ServiceError('INVALID_SOURCE') from None
            connection.execute(text('INSERT INTO sources(id,project_id,format,revision,sha256,size,filename,created_at) VALUES(:id,:project,:format,:revision,:sha,:size,:filename,:time)'),{'id':source_id,'project':project_id,'format':format,'revision':revision,'sha':sha256,'size':len(data),'filename':filename,'time':int(self.clock())})
            self.accounts._audit(connection,actor.user_id,'register_source',source_id,'succeeded')
        return SourceSnapshot(source_id,project_id,format,revision,sha256,len(data))

    def read_source(self,actor,project_id,source_id):
        self.accounts.require_project(actor,project_id,'read')
        with self.store.transaction() as connection:
            row=connection.execute(text('SELECT * FROM sources WHERE id=:id AND project_id=:project'),{'id':source_id,'project':project_id}).mappings().first()
        if row is None: raise ServiceError('INVALID_SOURCE')
        try: return self.sources.read(project_id,row['filename'],row['size'],row['sha256'])
        except Exception: raise ServiceError('INVALID_SOURCE') from None
