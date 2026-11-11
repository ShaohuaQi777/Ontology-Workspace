"""Persisted authorized pure semantic jobs; no arbitrary commands or native objects."""
from dataclasses import dataclass
import hashlib,json,re,time,uuid
from sqlalchemy import text
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.semantic import dto
from ontology_platform.infrastructure.job_schema import initialize_job_schema
from ontology_platform.infrastructure.source_policy import checked_json
from .accounts import Principal

REQUESTS={'ingest':dto.IngestRequest,'parse':dto.ParseRequest,'extract':dto.ExtractRequest,'build_graph':dto.GraphBuildRequest,'ontology':dto.OntologyRequest,'validate_shacl':dto.SHACLRequest,'reason':dto.ReasoningRequest}


@dataclass(frozen=True)
class Job:
    job_id:str
    project_id:str
    operation:str
    state:str
    attempt:int
    run_id:str
    replay_of:str|None
    error_code:str|None
    result:dict|None


class JobService:
    def __init__(self,store,accounts,workspaces,clock=time.time):
        self.store=store; self.accounts=accounts; self.workspaces=workspaces; self.clock=clock

    def initialize(self): initialize_job_schema(self.store)

    @staticmethod
    def _action(operation): return 'read' if operation=='validate_shacl' else 'edit'

    @staticmethod
    def _key(value):
        if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',value): raise ServiceError('INVALID_JOB')
        return value

    @staticmethod
    def _job(row):
        return Job(row['id'],row['project_id'],row['operation'],row['state'],row['attempt'],row['run_id'],row['replay_of'],row['error_code'],json.loads(row['result_json']) if row['result_json'] else None)

    def _event(self,connection,job_id,state):
        connection.execute(text('INSERT INTO job_events(job_id,state,created_at) VALUES(:job,:state,:time)'),{'job':job_id,'state':state,'time':int(self.clock())})

    def _row(self,connection,job_id,project_id=None):
        row=connection.execute(text('SELECT * FROM jobs WHERE id=:job'),{'job':job_id}).mappings().first()
        if row is None or (project_id is not None and row['project_id']!=project_id): raise ServiceError('INVALID_JOB')
        return row

    def _restore_actor(self,connection,row):
        user=self.accounts._session(connection,row['session_digest'])
        if user['id']!=row['actor_id']: raise ServiceError('UNAUTHENTICATED')
        digest=row['session_digest']
        return Principal(user['id'],user['username'],user['global_role'],digest,self.accounts._proof(user['id'],user['username'],user['global_role'],digest))

    def submit(self,actor,project_id,operation,request,expected_workspace_revision,idempotency_key):
        if operation not in REQUESTS: raise ServiceError('INVALID_JOB')
        self._key(idempotency_key); self.accounts.require_project(actor,project_id,self._action(operation))
        try:
            payload=request.model_dump(mode='json') if hasattr(request,'model_dump') else request
            value=REQUESTS[operation].model_validate_json(json.dumps(checked_json(payload),allow_nan=False))
        except Exception: raise ServiceError('INVALID_JOB') from None
        bindings={}; payload=value.model_dump(mode='json')
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.accounts.require_project(actor,project_id,self._action(operation))
            current=connection.execute(text('SELECT workspace_revision FROM projects WHERE id=:project'),{'project':project_id}).scalar_one()
            if current!=expected_workspace_revision: raise ServiceError('STALE_REVISION')
            for key in ('source','shapes','rules'):
                if not hasattr(value,key): continue
                ref=getattr(value,key)
                source=connection.execute(text('SELECT * FROM sources WHERE id=:id AND project_id=:project'),{'id':ref.path,'project':project_id}).mappings().first()
                if source is None or (ref.sha256,ref.size,ref.revision)!=(source['sha256'],source['size'],source['revision']): raise ServiceError('INVALID_SOURCE')
                self.workspaces.read_source(actor,project_id,source['id'])
                bindings[key]={field:source[field] for field in ('id','format','revision','sha256','size')}
            if set(value.source_refs)!={'source:'+source['id'] for source in bindings.values()}: raise ServiceError('INVALID_SOURCE')
            if operation in ('ingest','parse') and value.format!=bindings['source']['format']: raise ServiceError('INVALID_SOURCE')
            payload.update(run_id='server-assigned',workspace_revision=current,scope_ref='scope:'+project_id,source_refs=sorted({'source:'+source['id'] for source in bindings.values()}))
            for key in bindings:
                payload[key]['kind']=bindings[key]['format']
            for key,field in [('source_revision','source'),('graph_revision','source'),('schema_revision','source'),('shapes_revision','shapes'),('ruleset_revision','rules')]:
                if key in payload: payload[key]=bindings[field]['revision']
            canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)
            input_hash=hashlib.sha256((operation+'\n'+canonical).encode()).hexdigest()
            existing=connection.execute(text('SELECT * FROM jobs WHERE project_id=:project AND actor_id=:actor AND idempotency_key=:key'),{'project':project_id,'actor':actor.user_id,'key':idempotency_key}).mappings().first()
            if existing:
                if existing['input_hash']!=input_hash: raise ServiceError('IDEMPOTENCY_CONFLICT')
                return self._job(existing)
            job_id=str(uuid.uuid4()); run_id='run-'+uuid.uuid4().hex
            payload['run_id']=run_id
            connection.execute(text("INSERT INTO jobs(id,project_id,actor_id,session_digest,operation,request_json,bindings_json,workspace_revision,idempotency_key,input_hash,run_id,state,created_at) VALUES(:id,:project,:actor,:digest,:operation,:request,:bindings,:workspace,:key,:hash,:run,'pending',:time)"),{'id':job_id,'project':project_id,'actor':actor.user_id,'digest':actor._session_hash,'operation':operation,'request':json.dumps(payload,ensure_ascii=False,separators=(',',':')),'bindings':json.dumps(bindings,separators=(',',':')),'workspace':current,'key':idempotency_key,'hash':input_hash,'run':run_id,'time':int(self.clock())})
            self._event(connection,job_id,'pending')
            return self._job(self._row(connection,job_id))

    def get(self,actor,project_id,job_id):
        self.accounts.require_project(actor,project_id,'read')
        with self.store.transaction() as connection: return self._job(self._row(connection,job_id,project_id))

    def _family_attempts(self,connection,row):
        seen=set(); root=row
        while root['replay_of']:
            if root['id'] in seen: raise ServiceError('UNSAFE_REPLAY')
            seen.add(root['id']); root=self._row(connection,root['replay_of'])
        return connection.execute(text("WITH RECURSIVE family(id) AS (SELECT :root UNION SELECT j.id FROM jobs j JOIN family f ON j.replay_of=f.id) SELECT COUNT(*) FROM job_events e JOIN family f ON e.job_id=f.id WHERE e.state='running'"),{'root':root['id']}).scalar_one()

    def claim(self,worker_id):
        self._key(worker_id)
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            while True:
                row=connection.execute(text("SELECT * FROM jobs WHERE state='pending' AND cancel_requested=0 AND attempt<3 ORDER BY rowid LIMIT 1")).mappings().first()
                if row is None: return None
                if self._family_attempts(connection,row)<3: break
                connection.execute(text("UPDATE jobs SET state='failed',error_code='ATTEMPT_LIMIT' WHERE id=:id"),{'id':row['id']})
                self._event(connection,row['id'],'failed')
            connection.execute(text("UPDATE jobs SET state='running',attempt=attempt+1,worker_id=:worker,heartbeat=:time WHERE id=:id AND state='pending'"),{'worker':worker_id,'time':int(self.clock()),'id':row['id']})
            self._event(connection,row['id'],'running')
            return self._job(self._row(connection,row['id']))

    def heartbeat(self,job_id,worker_id):
        with self.store.transaction() as connection:
            result=connection.execute(text("UPDATE jobs SET heartbeat=:time WHERE id=:id AND worker_id=:worker AND state='running'"),{'time':int(self.clock()),'id':job_id,'worker':worker_id})
            return result.rowcount==1

    def cancel(self,actor,project_id,job_id):
        self.accounts.require_project(actor,project_id,'edit')
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE'); row=self._row(connection,job_id,project_id)
            if row['state'] not in ('pending','running'): return
            state='cancelled' if row['state']=='pending' else 'running'
            connection.execute(text('UPDATE jobs SET cancel_requested=1,state=:state WHERE id=:id'),{'state':state,'id':job_id})
            self._event(connection,job_id,'cancel_requested' if state=='running' else state)

    def recover_interrupted(self,worker_id):
        self._key(worker_id)
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            ids=list(connection.execute(text("SELECT id FROM jobs WHERE state='running' AND worker_id=:worker"),{'worker':worker_id}).scalars())
            connection.execute(text("UPDATE jobs SET state='interrupted',error_code='INTERRUPTED' WHERE state='running' AND worker_id=:worker"),{'worker':worker_id})
            for job_id in ids: self._event(connection,job_id,'interrupted')

    def replay(self,actor,project_id,job_id,idempotency_key):
        self._key(idempotency_key); self.accounts.require_project(actor,project_id,'edit')
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE'); row=self._row(connection,job_id,project_id)
            if row['operation'] not in REQUESTS or row['state'] not in ('failed','cancelled','interrupted') or row['attempt']>=3: raise ServiceError('UNSAFE_REPLAY')
            # Explicit replay is a new authorized request, not a renewal of the old session.
            self.accounts._actor(connection,actor)
            self.accounts.require_project(actor,project_id,'edit')
            if self._family_attempts(connection,row)>=3: raise ServiceError('UNSAFE_REPLAY')
            current=connection.execute(text('SELECT workspace_revision FROM projects WHERE id=:project'),{'project':project_id}).scalar_one()
            if current!=row['workspace_revision']: raise ServiceError('STALE_REVISION')
            self._check_bindings(connection,row)
            for source in json.loads(row['bindings_json']).values(): self.workspaces.read_source(actor,project_id,source['id'])
            existing=connection.execute(text('SELECT * FROM jobs WHERE project_id=:project AND actor_id=:actor AND idempotency_key=:key'),{'project':project_id,'actor':actor.user_id,'key':idempotency_key}).mappings().first()
            if existing:
                if existing['replay_of']!=job_id: raise ServiceError('IDEMPOTENCY_CONFLICT')
                return self._job(existing)
            new_id=str(uuid.uuid4()); run_id='run-'+uuid.uuid4().hex; payload=json.loads(row['request_json']); payload['run_id']=run_id
            connection.execute(text("INSERT INTO jobs(id,project_id,actor_id,session_digest,operation,request_json,bindings_json,workspace_revision,idempotency_key,input_hash,run_id,replay_of,state,attempt,created_at) VALUES(:id,:project,:actor,:digest,:operation,:request,:bindings,:workspace,:key,:hash,:run,:replay,'pending',:attempt,:time)"),{'id':new_id,'project':project_id,'actor':actor.user_id,'digest':actor._session_hash,'operation':row['operation'],'request':json.dumps(payload,separators=(',',':')),'bindings':row['bindings_json'],'workspace':row['workspace_revision'],'key':idempotency_key,'hash':row['input_hash'],'run':run_id,'replay':job_id,'attempt':row['attempt'],'time':int(self.clock())})
            self._event(connection,new_id,'pending')
            return self._job(self._row(connection,new_id))

    def _check_bindings(self,connection,row):
        for expected in json.loads(row['bindings_json']).values():
            current=connection.execute(text('SELECT id,format,revision,sha256,size FROM sources WHERE id=:id AND project_id=:project'),{'id':expected['id'],'project':row['project_id']}).mappings().first()
            if current is None or dict(current)!=expected: raise ServiceError('INVALID_SOURCE')

    def prepare(self,job_id,worker_id):
        with self.store.transaction() as connection:
            row=dict(self._row(connection,job_id))
            if row['state']!='running' or row['worker_id']!=worker_id: raise ServiceError('INVALID_JOB')
            actor=self._restore_actor(connection,row)
            self.accounts.require_project(actor,row['project_id'],self._action(row['operation']))
            current=connection.execute(text('SELECT workspace_revision FROM projects WHERE id=:project'),{'project':row['project_id']}).scalar_one()
            if current!=row['workspace_revision']: raise ServiceError('STALE_REVISION')
            self._check_bindings(connection,row)
        inputs={}
        for key,source in json.loads(row['bindings_json']).items():
            inputs[key]=self.workspaces.read_source(actor,row['project_id'],source['id'])
            if hashlib.sha256(inputs[key]).hexdigest()!=source['sha256'] or len(inputs[key])!=source['size']: raise ServiceError('INVALID_SOURCE')
        return row,inputs

    def finish(self,job_id,worker_id,result=None,error_code=None):
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE'); row=self._row(connection,job_id)
            if row['state']!='running' or row['worker_id']!=worker_id: return
            state='failed'; serialized=None
            if row['cancel_requested']: state='cancelled'; error_code=None
            elif result is not None:
                try:
                    actor=self._restore_actor(connection,row)
                    self.accounts.require_project(actor,row['project_id'],self._action(row['operation']))
                    current=connection.execute(text('SELECT workspace_revision FROM projects WHERE id=:project'),{'project':row['project_id']}).scalar_one()
                    if current!=row['workspace_revision']: raise ServiceError('STALE_REVISION')
                    self._check_bindings(connection,row)
                    for source in json.loads(row['bindings_json']).values():
                        contents=self.workspaces.read_source(actor,row['project_id'],source['id'])
                        if hashlib.sha256(contents).hexdigest()!=source['sha256']: raise ServiceError('INVALID_SOURCE')
                    serialized=result.model_dump_json(); state='succeeded'
                except ServiceError as failure: error_code=failure.code
            connection.execute(text("UPDATE jobs SET state=:state,result_json=:result,error_code=:error WHERE id=:id AND state='running' AND worker_id=:worker"),{'state':state,'result':serialized,'error':error_code,'id':job_id,'worker':worker_id})
            self._event(connection,job_id,state)

    def read_artifact(self,actor,project_id,job_id,path):
        job=self.get(actor,project_id,job_id)
        if job.state!='succeeded' or not job.result: raise ServiceError('INVALID_JOB')
        ref=next((value for value in job.result['artifact_refs'] if value['path']==path),None)
        if ref is None: raise ServiceError('INVALID_JOB')
        from ontology_platform.infrastructure.job_artifacts import JobArtifacts
        return JobArtifacts(self.workspaces.sources.root).read(project_id,job_id,path,ref['size'],ref['sha256'])
