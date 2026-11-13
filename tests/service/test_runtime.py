"""Real local process/SQLite/native lifecycle, no business scenario or fake backend."""
import importlib,json,os,socket,subprocess,sys,time
from pathlib import Path
import httpx,pytest
from test_jobs import queue,submit
from test_workspaces import workspace
from test_accounts import PASSWORD


def wait_until(check,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=check()
        if result: return result
        time.sleep(.05)
    raise AssertionError('Actual runtime did not reach the bounded expected condition')


def test_owned_worker_auto_consumes_actual_native_job_and_excludes_second_owner(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path)
    cls=importlib.import_module('ontology_platform.application.runtime').LocalWorkerRuntime
    first=cls(jobs,'local-worker'); first.start()
    try:
        second=cls(jobs,'local-worker')
        with pytest.raises(Exception) as busy: second.start()
        assert str(busy.value)=='SERVICE_ALREADY_RUNNING'
        job=submit(jobs,actor,project,source)
        result=wait_until(lambda: (value if (value:=jobs.get(actor,project.project_id,job.job_id)).state=='succeeded' else None))
        assert result.result['data']['file_type']=='csv'
    finally: first.stop(); store.close()


def service_process(tmp_path,store,root):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); port=listener.getsockname()[1]
    origin=f'http://127.0.0.1:{port}'
    args=[sys.executable,'-m','ontology_platform.api.server','--database','sqlite:///'+str(store.database_path),'--artifact-root',str(root),'--origin',origin,'--port',str(port),'--insecure-dev']
    process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'PYTHONPATH':str(Path('src').absolute())})
    client=httpx.Client(base_url=origin,headers={'Origin':origin},timeout=3)
    def healthy():
        if process.poll() is not None: raise AssertionError('Actual local HTTP server exited before health')
        try: return client.get('/healthz').status_code==200
        except httpx.TransportError: return False
    try: wait_until(healthy)
    except BaseException:
        process.terminate(); process.wait(timeout=10); client.close(); raise
    return process,client,origin,args


def test_cli_single_user_flag_is_explicit_and_loopback_only(tmp_path):
    from ontology_platform.api.server import parse_args
    settings=parse_args(['--database','sqlite:///'+str(tmp_path/'metadata.db'),'--artifact-root',str(tmp_path/'artifacts'),'--origin','http://127.0.0.1:4173','--single-user'])
    assert settings.single_user is True and settings.host=='127.0.0.1'


def stop(process,client):
    if process.poll() is None:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
    client.close()


def upload_and_queue(client,pid,operation='parse',data=b'id,value\nn1,7\n',format='csv'):
    source=client.post(f'/api/projects/{pid}/sources',params={'format':format},content=data,headers={'Content-Type':'application/octet-stream'}).json()
    from test_jobs import request
    from types import SimpleNamespace
    payload=request(operation,SimpleNamespace(**source)).model_dump(mode='json')
    response=client.post(f'/api/projects/{pid}/jobs',json={'operation':operation,'request':payload,'expected_workspace_revision':'w0','idempotency_key':'runtime-'+operation})
    assert response.status_code==202,response.text
    return source,response.json()


def test_real_loopback_http_native_results_restart_persistence_and_scope(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path)
    process,client,origin,args=service_process(tmp_path,store,root)
    try:
        assert client.get('/readyz').status_code==200
        assert client.get('/api/session/me',headers={'X-Role':'admin'}).status_code==401
        response=client.post('/api/session/login',json={'username':'root','password':PASSWORD}); assert response.status_code==200
        assert 'httponly' in response.headers['set-cookie'].lower() and 'samesite=strict' in response.headers['set-cookie'].lower()
        project=client.post('/api/projects',json={'name':'Technical','namespace':'urn:runtime:'}).json(); pid=project['project_id']
        source,job=upload_and_queue(client,pid)
        url='/api/jobs/'+job['run_id']
        result=wait_until(lambda: (value if (value:=client.get(url).json()).get('state')=='succeeded' else None))
        assert result['result']['data']['rows']==[{'id':'n1','value':'7'}]
        assert [event['state'] for event in client.get(url+'/events').json()['items']]==['pending','running','succeeded']
        assert client.get(url+'/artifacts/0').status_code==200
        bad=client.post('/api/projects',json={'name':'Refused','namespace':'urn:denied:'},headers={'Origin':'https://outside.invalid'}); assert bad.status_code==403
        cookies=dict(client.cookies)
        stop(process,client)
        process,client,origin,args=service_process(tmp_path,store,root); client.cookies.update(cookies)
        assert client.get(url).json()['state']=='succeeded'
        assert client.get(f'/api/projects/{pid}/sources/{source["source_id"]}').content==b'id,value\nn1,7\n'
        assert client.get('/readyz').status_code==200
    finally: stop(process,client); store.close()


def test_actual_crash_running_job_is_interrupted_not_blindly_retried(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path)
    process,client,origin,args=service_process(tmp_path,store,root)
    try:
        assert client.post('/api/session/login',json={'username':'root','password':PASSWORD}).status_code==200
        project=client.post('/api/projects',json={'name':'Technical','namespace':'urn:crash:'}).json(); pid=project['project_id']
        source,job=upload_and_queue(client,pid,'extract',b'Apple acquired Microsoft in California. '*100,'text')
        url='/api/jobs/'+job['run_id']
        wait_until(lambda:client.get(url).json().get('state')=='running')
        process.kill(); process.wait(timeout=5); cookies=dict(client.cookies); client.close()
        process,client,origin,args=service_process(tmp_path,store,root); client.cookies.update(cookies)
        old=client.get(url).json(); assert old['state']=='interrupted' and old['result'] is None
        replay=client.post(url+'/replay',json={'idempotency_key':'explicit-runtime-replay'})
        assert replay.status_code==202,replay.text
        new=replay.json(); assert new['run_id']!=job['run_id'] and new['replay_of']==job['job_id']
        def succeeded():
            value=client.get('/api/jobs/'+new['run_id']).json()
            assert value.get('state') not in ('failed','cancelled','interrupted'),(value.get('state'),value.get('error_code'))
            return value if value.get('state')=='succeeded' else None
        result=wait_until(succeeded,timeout=40)
        assert result['result']['data']['entities'] and client.get(url).json()['state']=='interrupted'
    finally: stop(process,client); store.close()
