"""Real ASGI service requests; technical local accounts, never live credentials."""
import asyncio,importlib,json
import httpx,pytest
from sqlalchemy import text
from test_workspaces import workspace
from test_accounts import TestSecrets,PASSWORD
from test_jobs import request as semantic_request

ORIGIN='https://tool.invalid'


def api(tmp_path,provider=None,secure=True):
    work,accounts,store,actor,root=workspace(tmp_path)
    module=importlib.import_module('ontology_platform.api.app')
    app=module.create_app(store,root,provider or TestSecrets(),[ORIGIN],secure_cookies=secure)
    return app,store,root


async def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN,headers={'Origin':ORIGIN})


async def login(c):
    response=await c.post('/api/session/login',json={'username':'root','password':PASSWORD})
    assert response.status_code==200,response.text
    return response


def test_health_ready_cookie_me_logout_and_no_identity_header_trust(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            assert (await c.get('/healthz')).json()=={'status':'ok'}
            assert (await c.get('/readyz')).status_code==200
            assert (await c.get('/api/session/me',headers={'X-User-ID':'root','X-Role':'admin'})).status_code==401
            response=await login(c); cookie=response.headers['set-cookie'].lower()
            assert 'httponly' in cookie and 'secure' in cookie and 'samesite=strict' in cookie
            assert 'password' not in response.text and 'token' not in response.text
            assert (await c.get('/api/session/me')).json()['username']=='root'
            assert (await c.get('/docs')).status_code==404
            assert (await c.post('/api/session/logout',json={})).status_code==200
            assert (await c.get('/api/session/me')).status_code==401
    asyncio.run(run()); store.close()


def test_explicit_single_user_mode_opens_workspace_without_login_form_or_cookie(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path)
    module=importlib.import_module('ontology_platform.api.app')
    app=module.create_app(store,root,TestSecrets(),[ORIGIN],single_user=True)
    async def run():
        async with await client(app) as c:
            me=await c.get('/api/session/me')
            assert me.status_code==200 and me.json()['username']=='workspace'
            assert 'set-cookie' not in me.headers
            project=await c.post('/api/projects',json={'name':'No login workspace','namespace':'urn:single-user:'})
            assert project.status_code==201
            assert (await c.get('/api/projects')).json()['items'][0]['project_id']==project.json()['project_id']
    asyncio.run(run()); store.close()


@pytest.mark.parametrize('origin',[None,'https://outside.invalid','null'])
def test_write_origin_csrf_rejects_before_login(tmp_path,origin):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            if origin is None: del c.headers['Origin']
            else: c.headers['Origin']=origin
            response=await c.post('/api/session/login',json={'username':'root','password':PASSWORD})
            assert response.status_code==403
            assert PASSWORD not in response.text
    asyncio.run(run()); store.close()


def test_json_type_and_validation_errors_do_not_echo_private_inputs(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            response=await c.post('/api/session/login',content='password=PRIVATE-MARKER',headers={'Content-Type':'application/x-www-form-urlencoded'})
            assert response.status_code==415 and 'PRIVATE-MARKER' not in response.text
            response=await c.post('/api/session/login',json={'username':{'private':'PRIVATE-MARKER'},'password':PASSWORD,'token':'PRIVATE-MARKER'})
            assert response.status_code==422 and 'PRIVATE-MARKER' not in response.text and PASSWORD not in response.text
            assert set(response.json())=={'code','run_id'}
    asyncio.run(run()); store.close()


@pytest.mark.parametrize('raw',[False,True])
def test_chunked_body_limit_is_enforced_without_trusting_length(tmp_path,raw):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            await login(c)
            project=(await c.post('/api/projects',json={'name':'Technical','namespace':'urn:api:'})).json()
            path='/api/projects/'+project['project_id']+'/sources?format=text' if raw else '/api/projects'
            async def chunks():
                for _ in range(20): yield b'x'*(65536 if raw else 8192)
            response=await c.post(path,content=chunks(),headers={'Content-Type':'application/octet-stream' if raw else 'application/json','Content-Length':'1'})
            assert response.status_code==413 and 'xxxxx' not in response.text
    asyncio.run(run()); store.close()


def test_workspace_cas_sources_queue_native_worker_events_artifact_and_scope(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            await login(c)
            project=(await c.post('/api/projects',json={'name':'Technical','namespace':'urn:api:'})).json(); pid=project['project_id']
            assert (await c.get('/api/projects')).json()['items'][0]['project_id']==pid
            revision=await c.put('/api/projects/'+pid+'/layers/tbox',json={'base_revision':'w0','content':{'classes':[]},'dependencies':{}})
            assert revision.status_code==200
            stale=await c.put('/api/projects/'+pid+'/layers/tbox',json={'base_revision':'w0','content':{},'dependencies':{}})
            assert stale.status_code==409
            source=(await c.post('/api/projects/'+pid+'/sources?format=csv',content=b'id,value\nn1,7\n',headers={'Content-Type':'application/octet-stream'})).json()
            from types import SimpleNamespace
            payload=semantic_request('parse',SimpleNamespace(**source)).model_dump(mode='json')
            queued=await c.post('/api/projects/'+pid+'/jobs',json={'operation':'parse','request':payload,'expected_workspace_revision':revision.json()['revision_id'],'idempotency_key':'api-technical'})
            assert queued.status_code==202,queued.text
            job=queued.json(); assert job['state']=='pending'
            assert app.state.worker.run_one('api-worker')
            completed=(await c.get('/api/jobs/'+job['run_id'])).json()
            assert completed['state']=='succeeded' and completed['result']['data']['rows']==[{'id':'n1','value':'7'}]
            events=(await c.get('/api/jobs/'+job['run_id']+'/events')).json()['items']
            assert [item['state'] for item in events]==['pending','running','succeeded']
            response=await c.get('/api/jobs/'+job['run_id']+'/artifacts/0'); assert response.status_code==200
            assert (await c.get('/api/jobs/'+job['run_id']+'/artifacts/999')).status_code==404
            other=(await c.post('/api/projects',json={'name':'Other','namespace':'urn:other:'})).json()
            scoped=await c.get('/api/projects/'+other['project_id']+'/sources/'+source['source_id'])
            assert scoped.status_code==404
    asyncio.run(run()); store.close()


def test_project_membership_and_job_reads_reject_nonmember_despite_headers(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as admin:
            await login(admin)
            project=(await admin.post('/api/projects',json={'name':'Technical','namespace':'urn:private:'})).json()
            created=await admin.post('/api/accounts',json={'username':'outsider','password_ref':'test:password'})
            assert created.status_code==201
            async with await client(app) as outsider:
                response=await outsider.post('/api/session/login',json={'username':'outsider','password':PASSWORD}); assert response.status_code==200
                denied=await outsider.get('/api/projects/'+project['project_id']+'/members',headers={'X-Role':'owner'})
                assert denied.status_code==403
                assert (await outsider.get('/api/projects')).json()['items']==[]
    asyncio.run(run()); store.close()


def test_member_grant_and_removal_are_explicit_authorized_and_audited(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as admin:
            await login(admin)
            project=(await admin.post('/api/projects',json={'name':'Technical','namespace':'urn:members:'})).json(); pid=project['project_id']
            user=(await admin.post('/api/accounts',json={'username':'reader','password_ref':'test:password'})).json()
            async with await client(app) as reader:
                await reader.post('/api/session/login',json={'username':'reader','password':PASSWORD})
                path='/api/projects/'+pid+'/members'
                assert (await reader.post(path,json={'user_id':user['user_id'],'role':'owner'},headers={'X-Role':'owner'})).status_code==403
                granted=await admin.post(path,json={'user_id':user['user_id'],'role':'engineer'}); assert granted.status_code==201
                assert (await reader.get('/api/projects/'+pid+'/sources')).status_code==200
                removed=await admin.request('DELETE',path+'/'+user['user_id']+'/engineer',json={})
                assert removed.status_code==200
                assert (await reader.get('/api/projects/'+pid+'/sources')).status_code==403
    asyncio.run(run())
    with store.transaction() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM audit_events WHERE action IN ('set_member','remove_member')")).scalar_one()==2
    store.close()


@pytest.mark.parametrize('origins',[[],['*'],['https://alice:PRIVATE-MARKER@tool.invalid'],['http://remote.invalid']])
def test_invalid_origin_configuration_fails_at_startup_not_first_request(tmp_path,origins):
    work,accounts,store,actor,root=workspace(tmp_path)
    factory=importlib.import_module('ontology_platform.api.app').create_app
    with pytest.raises(ValueError) as failure: factory(store,root,TestSecrets(),origins)
    assert 'PRIVATE-MARKER' not in str(failure.value)
    store.close()


def test_overlong_untrusted_content_length_is_rejected_without_parser_exception(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            response=await c.get('/healthz',headers={'Content-Length':'9'*5000})
            assert response.status_code==400 and set(response.json())=={'code','run_id'}
    asyncio.run(run()); store.close()


def test_all_http_errors_have_fixed_code_and_server_generated_request_id(tmp_path):
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            response=await c.get('/unknown/PRIVATE-MARKER',headers={'X-Request-ID':'PRIVATE-MARKER'})
            assert response.status_code==404
            assert set(response.json())=={'code','run_id'} and 'PRIVATE-MARKER' not in response.text
    asyncio.run(run()); store.close()


def test_secret_provider_failure_is_sanitized_and_default_secure_cookie_remains(tmp_path):
    class Missing:
        def resolve(self,ref): raise RuntimeError('PRIVATE-SECRET-PROVIDER-MARKER')
    app,store,root=api(tmp_path,Missing())
    async def run():
        async with await client(app) as c:
            await login(c)
            response=await c.post('/api/accounts',json={'username':'other','password_ref':'env:ONTOLOGY_SECRET_ABSENT'})
            assert response.status_code==503 and 'PRIVATE-SECRET-PROVIDER-MARKER' not in response.text
    asyncio.run(run()); store.close()
