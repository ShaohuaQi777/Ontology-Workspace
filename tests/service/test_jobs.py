"""Actual durable queue state/permissions and native runs, no product fake backend."""
import importlib,json
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from ontology_platform.semantic import dto
from test_workspaces import workspace

TYPES={'ingest':dto.IngestRequest,'parse':dto.ParseRequest,'extract':dto.ExtractRequest,'build_graph':dto.GraphBuildRequest,'ontology':dto.OntologyRequest,'validate_shacl':dto.SHACLRequest,'reason':dto.ReasoningRequest}


def queue(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path)
    project=work.create_project(actor,'Jobs','urn:jobs:')
    source=work.register_source(actor,project.project_id,'csv',b'id,value\nn1,7\n')
    module=importlib.import_module('ontology_platform.application.jobs')
    jobs=module.JobService(store,accounts,work); jobs.initialize()
    return jobs,work,accounts,store,actor,root,project,source


def request(operation,source,**extras):
    ref=lambda value:dto.ArtifactRef(path=value.source_id,sha256=value.sha256,size=value.size,kind=value.format,revision=value.revision)
    common={'run_id':'client-run','workspace_revision':'w0','source_refs':tuple('source:'+value.source_id for value in [source,*[v for k,v in extras.items() if k in ('shapes','rules')]]),'scope_ref':'scope:client-context','source':ref(source)}
    fields={'ingest':{'source_revision':source.revision,'format':source.format},'parse':{'source_revision':source.revision,'format':source.format},'extract':{'source_revision':source.revision},'build_graph':{'graph_revision':source.revision},'ontology':{'schema_revision':source.revision,'action':'import','format':'turtle'},'validate_shacl':{'graph_revision':source.revision,'shapes_revision':extras['shapes'].revision,'suite_revision':'technical-suite'} if operation=='validate_shacl' else {},'reason':{'graph_revision':source.revision,'ruleset_revision':extras['rules'].revision} if operation=='reason' else {}}[operation]
    for key,val in extras.items(): fields[key]=ref(val) if key in ('shapes','rules') else val
    return TYPES[operation](**common,**fields)


def submit(jobs,actor,project,source,key='technical-key',operation='ingest',**extras):
    return jobs.submit(actor,project.project_id,operation,request(operation,source,**extras),'w0',key)


def test_atomic_claim_and_idempotency_bound_to_content(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path)
    one=submit(jobs,actor,project,source)
    assert submit(jobs,actor,project,source).job_id==one.job_id
    changed=work.register_source(actor,project.project_id,'csv',b'id,value\nn2,8\n')
    with pytest.raises(Exception) as collision: submit(jobs,actor,project,changed)
    assert collision.value.code=='IDEMPOTENCY_CONFLICT'
    with pytest.raises(Exception) as other_operation: submit(jobs,actor,project,source,operation='parse')
    assert other_operation.value.code=='IDEMPOTENCY_CONFLICT'
    with ThreadPoolExecutor(max_workers=2) as pool: claims=list(pool.map(jobs.claim,['worker-a','worker-b']))
    assert sum(item is not None for item in claims)==1
    assert jobs.get(actor,project.project_id,one.job_id).state=='running'
    store.close()


def test_pending_cancel_and_restart_running_interrupted_with_explicit_replay(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path)
    pending=submit(jobs,actor,project,source); jobs.cancel(actor,project.project_id,pending.job_id)
    assert jobs.get(actor,project.project_id,pending.job_id).state=='cancelled' and jobs.claim('worker-a') is None
    running=submit(jobs,actor,project,source,key='second'); claimed=jobs.claim('worker-a')
    assert claimed.attempt==1
    jobs.recover_interrupted('worker-a')
    assert jobs.get(actor,project.project_id,running.job_id).state=='interrupted'
    assert jobs.claim('worker-a') is None
    replay=jobs.replay(actor,project.project_id,running.job_id,'replay-key')
    assert replay.run_id!=running.run_id and replay.replay_of==running.job_id
    assert jobs.get(actor,project.project_id,running.job_id).state=='interrupted'
    store.close()


def test_stale_workspace_and_foreign_source_rejected_before_job_persistence(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path)
    work.save_layer(actor,project.project_id,'tbox','w0',{}, {})
    with pytest.raises(Exception) as stale: submit(jobs,actor,project,source)
    assert stale.value.code=='STALE_REVISION'
    other=work.create_project(actor,'Other','urn:other:')
    with pytest.raises(Exception) as scoped: submit(jobs,actor,other,source)
    assert scoped.value.code=='INVALID_SOURCE'
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM jobs')).scalar_one()==0
    store.close()


@pytest.mark.parametrize('change',['disabled','workspace','hash','revision'])
def test_worker_rechecks_actor_workspace_and_source_before_native_call(tmp_path,change):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path)
    job=submit(jobs,actor,project,source)
    if change=='disabled':
        with store.transaction() as connection: connection.execute(text('UPDATE accounts SET disabled=1 WHERE id=:id'),{'id':actor.user_id})
    elif change=='workspace': work.save_layer(actor,project.project_id,'tbox','w0',{}, {})
    elif change=='revision':
        with store.transaction() as connection: connection.execute(text("UPDATE sources SET revision='changed-revision' WHERE id=:id"),{'id':source.source_id})
    else:
        file=next(path for path in root.rglob('*') if path.is_file()); file.write_bytes(b'corrupt')
    worker=importlib.import_module('ontology_platform.application.worker').NativeJobWorker(jobs)
    assert worker.run_one('worker-a')
    with store.transaction() as connection:
        row=connection.execute(text('SELECT state,result_json FROM jobs WHERE id=:id'),{'id':job.job_id}).one()
        assert row.state=='failed' and row.result_json is None
    assert not list(root.glob('*/jobs'))
    store.close()


def test_completed_native_run_result_and_artifact_scope_persist(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); job=submit(jobs,actor,project,source)
    worker=importlib.import_module('ontology_platform.application.worker').NativeJobWorker(jobs)
    assert worker.run_one('worker-a')
    finished=jobs.get(actor,project.project_id,job.job_id)
    assert finished.state=='succeeded' and finished.result['backend_version']=='0.7.0+ontologyworkspace.5'
    assert finished.result['data']['file_type']=='csv'
    ref=finished.result['artifact_refs'][0]
    assert jobs.read_artifact(actor,project.project_id,job.job_id,ref['path'])
    other=work.create_project(actor,'Other','urn:other:')
    with pytest.raises(Exception) as scoped: jobs.read_artifact(actor,other.project_id,job.job_id,ref['path'])
    assert scoped.value.code=='INVALID_JOB'
    store.close()


def test_running_cancel_after_actual_native_step_never_commits_success(tmp_path,monkeypatch):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); job=submit(jobs,actor,project,source)
    module=importlib.import_module('ontology_platform.application.worker')
    factory=module.create_backend
    def backend_with_cancel(kind,path):
        backend=factory(kind,path); ingest=backend.ingest
        def execute(value):
            result=ingest(value)
            jobs.cancel(actor,project.project_id,job.job_id)
            return result
        backend.ingest=execute
        return backend
    monkeypatch.setattr(module,'create_backend',backend_with_cancel)
    assert module.NativeJobWorker(jobs).run_one('worker-a')
    result=jobs.get(actor,project.project_id,job.job_id)
    assert result.state=='cancelled' and result.result is None
    store.close()


def test_explicit_replay_uses_fresh_authenticated_session_after_old_logout(tmp_path):
    from test_accounts import principal
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); job=submit(jobs,actor,project,source)
    jobs.claim('worker-a'); jobs.recover_interrupted('worker-a')
    with store.transaction() as connection:
        connection.execute(text('UPDATE sessions SET revoked=1 WHERE digest=:digest'),{'digest':actor._session_hash})
    current=principal(accounts)
    replay=jobs.replay(current,project.project_id,job.job_id,'new-session-replay')
    assert replay.replay_of==job.job_id and replay.state=='pending'
    store.close()


def test_safe_replay_family_cannot_bypass_three_attempts_by_branching(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); original=submit(jobs,actor,project,source)
    jobs.claim('worker-a'); jobs.recover_interrupted('worker-a')
    for key in ['branch-two','branch-three']:
        jobs.replay(actor,project.project_id,original.job_id,key)
        assert jobs.claim('worker-a') is not None
        jobs.recover_interrupted('worker-a')
    with pytest.raises(Exception) as limited: jobs.replay(actor,project.project_id,original.job_id,'branch-four')
    assert limited.value.code=='UNSAFE_REPLAY'
    store.close()


def test_claim_budget_is_atomic_for_already_queued_replay_branches(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); original=submit(jobs,actor,project,source)
    jobs.claim('worker-a'); jobs.recover_interrupted('worker-a')
    branches=[jobs.replay(actor,project.project_id,original.job_id,'queued-'+str(index)) for index in range(3)]
    for _ in range(2):
        assert jobs.claim('worker-a') is not None; jobs.recover_interrupted('worker-a')
    assert jobs.claim('worker-a') is None
    assert jobs.get(actor,project.project_id,branches[-1].job_id).state=='failed'
    store.close()


def test_unsafe_operation_is_not_replayed_and_claim_heartbeat_is_owner_bound(tmp_path):
    jobs,work,accounts,store,actor,root,project,source=queue(tmp_path); job=submit(jobs,actor,project,source)
    jobs.claim('worker-a')
    assert jobs.heartbeat(job.job_id,'worker-a') is True
    assert jobs.heartbeat(job.job_id,'worker-b') is False
    jobs.recover_interrupted('worker-a')
    with store.transaction() as connection: connection.execute(text("UPDATE jobs SET operation='deploy' WHERE id=:id"),{'id':job.job_id})
    with pytest.raises(Exception) as unsafe: jobs.replay(actor,project.project_id,job.job_id,'replay-key')
    assert unsafe.value.code=='UNSAFE_REPLAY'
    store.close()


@pytest.mark.parametrize('operation',['parse','extract','build_graph','ontology','validate_shacl','reason'])
def test_durable_worker_executes_actual_native_semantic_document_operations(tmp_path,operation):
    jobs,work,accounts,store,actor,root,project,_=queue(tmp_path)
    extras={}
    if operation=='parse': data=b'id,value\nn1,7\n'; format='csv'
    elif operation=='extract': data=b'Apple acquired Microsoft in California.'; format='text'
    elif operation=='build_graph': data=b'{"entities":[{"id":"n1","type":"Node"}],"relationships":[]}'; format='json'
    elif operation=='ontology': data=b'@prefix owl: <http://www.w3.org/2002/07/owl#> . <urn:Node> a owl:Class .'; format='turtle'
    elif operation=='validate_shacl':
        data=b'<urn:n> <urn:p> "v" .'; format='turtle'
        extras['shapes']=work.register_source(actor,project.project_id,'turtle',b'@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:S> a sh:NodeShape ; sh:targetNode <urn:n> ; sh:property [ sh:path <urn:p> ; sh:minCount 1 ] .')
    else:
        data=b'["Token(x)"]'; format='json'
        extras['rules']=work.register_source(actor,project.project_id,'json',b'[{"id":"r1","conditions":["Token(?x)"],"conclusion":"Mark(?x)"}]')
    source=work.register_source(actor,project.project_id,format,data)
    job=submit(jobs,actor,project,source,operation=operation,**extras)
    worker=importlib.import_module('ontology_platform.application.worker').NativeJobWorker(jobs); assert worker.run_one('worker-a')
    result=jobs.get(actor,project.project_id,job.job_id)
    assert result.state=='succeeded' and result.result['backend_version']=='0.7.0+ontologyworkspace.5'
    if operation=='parse': assert result.result['data']['rows']==[{'id':'n1','value':'7'}]
    elif operation=='extract':
        assert result.result['data']['entities']
        assert all(item['state']=='DRAFT' and item['confidence'] is None for item in result.result['data']['entities'])
    elif operation=='build_graph': assert len(result.result['data']['entities'])==1
    elif operation=='ontology': assert result.result['data']['format']=='nt'
    elif operation=='validate_shacl': assert result.result['data']['conforms'] is True
    else: assert result.result['data']['inferred'][0]['conclusion']=='Mark(x)'
    store.close()
