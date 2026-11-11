"""Authenticated tool-only HTTP composition; semantic operations stay in native Worker."""
from dataclasses import asdict
from importlib.metadata import version
from fastapi import FastAPI,Request,Response,Depends,Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import SecretStr
from sqlalchemy import text
from starlette.exceptions import HTTPException
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.application.accounts import AccountService,UserSummary
from ontology_platform.application.workspaces import WorkspaceService
from ontology_platform.application.jobs import JobService
from ontology_platform.application.worker import NativeJobWorker
from .auth import actor,COOKIE
from .middleware import BoundaryMiddleware
from .models import Login,AccountCreate,ProjectCreate,LayerSave,JobSubmit,Replay,Membership

STATUS={'UNAUTHENTICATED':401,'AUTHENTICATION_FAILED':401,'FORBIDDEN':403,'LOGIN_RATE_LIMIT':429,'SECRET_UNAVAILABLE':503,'STALE_REVISION':409,'NAMESPACE_CONFLICT':409,'IDEMPOTENCY_CONFLICT':409,'ACCOUNT_EXISTS':409,'INVALID_SOURCE':404,'INVALID_JOB':404,'INVALID_ACCOUNT':422}


def create_app(store,artifact_root,secret_provider,allowed_origins,secure_cookies=True):
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,debug=False)
    validated_boundary=BoundaryMiddleware(app,allowed_origins)
    accounts=AccountService(store,secret_provider); accounts.initialize()
    work=WorkspaceService(store,accounts,artifact_root); work.initialize()
    jobs=JobService(store,accounts,work); jobs.initialize()
    app.state.accounts=accounts; app.state.workspaces=work; app.state.jobs=jobs; app.state.worker=NativeJobWorker(jobs)
    app.add_middleware(BoundaryMiddleware,allowed_origins=validated_boundary.allowed)

    def failure(request,code,status): return JSONResponse({'code':code,'run_id':request.state.run_id},status_code=status)

    @app.exception_handler(ServiceError)
    async def service_error(request,exc): return failure(request,exc.code,STATUS.get(exc.code,400))

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return failure(request,{404:'NOT_FOUND',405:'METHOD_NOT_ALLOWED'}.get(exc.status_code,'HTTP_ERROR'),exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc): return failure(request,'INVALID_REQUEST',422)

    @app.exception_handler(Exception)
    async def internal_error(request,exc): return failure(request,'INTERNAL_ERROR',500)

    @app.get('/healthz')
    def health(): return {'status':'ok'}

    @app.get('/readyz')
    def ready(request:Request):
        try:
            with store.transaction() as connection: connection.execute(text('SELECT 1')).scalar_one()
            if version('semantica')!='0.7.0+ontologyworkspace.5': raise ValueError('Unsupported native version')
        except Exception: return failure(request,'NOT_READY',503)
        return {'status':'ready','backend_version':version('semantica')}

    @app.post('/api/session/login')
    def login(value:Login,response:Response):
        secret=accounts.login(value.username,value.password)
        current=accounts.resolve_session(secret)
        response.set_cookie(COOKIE,secret.get_secret_value(),max_age=28800,httponly=True,secure=secure_cookies,samesite='strict',path='/')
        return asdict(UserSummary(current.user_id,current.username,current.global_role))

    @app.get('/api/session/me')
    def me(current=Depends(actor)): return asdict(UserSummary(current.user_id,current.username,current.global_role))

    @app.post('/api/session/logout')
    def logout(request:Request,response:Response,current=Depends(actor)):
        accounts.revoke_session(SecretStr(request.cookies[COOKIE])); response.delete_cookie(COOKIE,path='/',httponly=True,secure=secure_cookies,samesite='strict')
        return {'status':'logged_out'}

    @app.post('/api/accounts',status_code=201)
    def create_account(value:AccountCreate,current=Depends(actor)):
        return asdict(accounts.create_user(current,value.username,value.password_ref))

    @app.post('/api/projects',status_code=201)
    def create_project(value:ProjectCreate,current=Depends(actor)):
        return asdict(work.create_project(current,value.name,value.namespace))

    @app.get('/api/projects')
    def projects(current=Depends(actor),limit:int=Query(default=50,ge=1,le=100),offset:int=Query(default=0,ge=0)):
        with store.transaction() as connection:
            rows=connection.execute(text('SELECT id AS project_id,name,namespace,workspace_revision FROM projects ORDER BY rowid LIMIT :limit OFFSET :offset'),{'limit':limit,'offset':offset}).mappings().all()
        visible=[]
        for row in rows:
            try: accounts.require_project(current,row['project_id'],'read')
            except ServiceError as exc:
                if exc.code!='FORBIDDEN': raise
                continue
            visible.append(dict(row))
        return {'items':visible}

    @app.get('/api/projects/{project_id}/members')
    def members(project_id:str,current=Depends(actor)):
        accounts.require_project(current,project_id,'manage_members')
        with store.transaction() as connection:
            rows=connection.execute(text('SELECT user_id,role FROM memberships WHERE project_id=:project ORDER BY user_id,role LIMIT 100'),{'project':project_id}).mappings().all()
        return {'items':[dict(row) for row in rows]}

    @app.post('/api/projects/{project_id}/members',status_code=201)
    def set_member(project_id:str,value:Membership,current=Depends(actor)):
        accounts.set_member(current,project_id,value.user_id,value.role)
        return {'user_id':value.user_id,'role':value.role}

    @app.delete('/api/projects/{project_id}/members/{user_id}/{role}')
    def remove_member(project_id:str,user_id:str,role:str,current=Depends(actor)):
        accounts.remove_member(current,project_id,user_id,role)
        return {'status':'removed'}

    @app.put('/api/projects/{project_id}/layers/{layer}')
    def save_layer(project_id:str,layer:str,value:LayerSave,current=Depends(actor)):
        return asdict(work.save_layer(current,project_id,layer,value.base_revision,value.content,value.dependencies))

    @app.get('/api/projects/{project_id}/layers')
    def layers(project_id:str,current=Depends(actor)):
        accounts.require_project(current,project_id,'read')
        with store.transaction() as connection:
            ids=connection.execute(text('SELECT id FROM revisions WHERE project_id=:project ORDER BY rowid DESC LIMIT 100'),{'project':project_id}).scalars().all()
        return {'items':[asdict(work.read_revision(current,project_id,key)) for key in ids]}

    @app.get('/api/projects/{project_id}/revisions/{revision_id}')
    def revision(project_id:str,revision_id:str,current=Depends(actor)):
        return asdict(work.read_revision(current,project_id,revision_id))

    @app.post('/api/projects/{project_id}/sources',status_code=201)
    async def upload(project_id:str,request:Request,format:str,current=Depends(actor)):
        return asdict(work.register_source(current,project_id,format,await request.body()))

    @app.get('/api/projects/{project_id}/sources')
    def sources(project_id:str,current=Depends(actor)):
        accounts.require_project(current,project_id,'read')
        with store.transaction() as connection:
            rows=connection.execute(text('SELECT id AS source_id,project_id,format,revision,sha256,size FROM sources WHERE project_id=:project ORDER BY rowid DESC LIMIT 100'),{'project':project_id}).mappings().all()
        return {'items':[dict(row) for row in rows]}

    @app.get('/api/projects/{project_id}/sources/{source_id}')
    def source(project_id:str,source_id:str,current=Depends(actor)):
        return Response(work.read_source(current,project_id,source_id),media_type='application/octet-stream')

    @app.post('/api/projects/{project_id}/jobs',status_code=202)
    def submit(project_id:str,value:JobSubmit,current=Depends(actor)):
        return asdict(jobs.submit(current,project_id,value.operation,value.request,value.expected_workspace_revision,value.idempotency_key))

    def run_row(run_id,current):
        with store.transaction() as connection:
            row=connection.execute(text('SELECT id,project_id FROM jobs WHERE run_id=:run'),{'run':run_id}).mappings().first()
        if row is None: raise ServiceError('INVALID_JOB')
        accounts.require_project(current,row['project_id'],'read')
        return row

    @app.get('/api/projects/{project_id}/jobs')
    def project_jobs(project_id:str,current=Depends(actor)):
        accounts.require_project(current,project_id,'read')
        with store.transaction() as connection:
            ids=connection.execute(text('SELECT id FROM jobs WHERE project_id=:project ORDER BY rowid DESC LIMIT 100'),{'project':project_id}).scalars().all()
        return {'items':[asdict(jobs.get(current,project_id,key)) for key in ids]}

    @app.get('/api/jobs/{run_id}')
    def get_job(run_id:str,current=Depends(actor)):
        row=run_row(run_id,current); return asdict(jobs.get(current,row['project_id'],row['id']))

    @app.get('/api/jobs/{run_id}/events')
    def events(run_id:str,current=Depends(actor)):
        row=run_row(run_id,current)
        with store.transaction() as connection:
            result=connection.execute(text('SELECT id,state,created_at FROM job_events WHERE job_id=:job ORDER BY id LIMIT 100'),{'job':row['id']}).mappings().all()
        return {'items':[dict(item) for item in result]}

    @app.post('/api/jobs/{run_id}/cancel')
    def cancel(run_id:str,current=Depends(actor)):
        row=run_row(run_id,current); jobs.cancel(current,row['project_id'],row['id'])
        return asdict(jobs.get(current,row['project_id'],row['id']))

    @app.post('/api/jobs/{run_id}/replay',status_code=202)
    def replay(run_id:str,value:Replay,current=Depends(actor)):
        row=run_row(run_id,current); return asdict(jobs.replay(current,row['project_id'],row['id'],value.idempotency_key))

    @app.get('/api/jobs/{run_id}/artifacts/{artifact_id}')
    def artifact(run_id:str,artifact_id:int,current=Depends(actor)):
        row=run_row(run_id,current); job=jobs.get(current,row['project_id'],row['id'])
        refs=job.result['artifact_refs'] if job.result else []
        if not 0<=artifact_id<len(refs): raise ServiceError('INVALID_JOB')
        return Response(jobs.read_artifact(current,row['project_id'],row['id'],refs[artifact_id]['path']),media_type='application/octet-stream')

    return app
