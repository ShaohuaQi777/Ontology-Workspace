"""Trusted aliases/CAS/project checks with real DB and account service."""
import importlib,json,os,sqlite3
from dataclasses import asdict
import pytest
from sqlalchemy import text
from test_workspaces import workspace


def setup(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path)
    project=work.create_project(actor,'Technical','urn:connections:')
    path=tmp_path/'readonly.db'
    with sqlite3.connect(path) as database: database.execute('CREATE TABLE technical(id TEXT)')
    path.chmod(0o600)
    domain=importlib.import_module('ontology_platform.domain.connections')
    targets=domain.TargetRegistry({'db':domain.Target('db','sqlite',str(path))},{'db':{project.project_id}})
    module=importlib.import_module('ontology_platform.application.connections')
    service=module.ConnectionService(store,accounts,targets); service.initialize()
    return service,work,accounts,store,actor,project,path,domain,module


def test_scoped_configured_connections_hide_server_paths_and_keep_history(tmp_path):
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    item=service.create(actor,project.project_id,'Technical source','db')
    assert item.status=='CONFIGURED' and item.target_alias=='db' and item.kind=='sqlite'
    assert str(path) not in json.dumps(asdict(item)) and str(path) not in repr(service.targets.resolve('db',project.project_id))
    assert service.get(actor,project.project_id,item.connection_id)==item
    assert service.list(actor,project.project_id)==[item]
    new=service.update(actor,project.project_id,item.connection_id,item.revision,'Renamed','db')
    assert new.revision!=item.revision and new.name=='Renamed'
    with pytest.raises(Exception) as stale: service.update(actor,project.project_id,item.connection_id,item.revision,'Old','db')
    assert stale.value.code=='STALE_REVISION'
    with store.transaction() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM connection_revisions')).scalar_one()==2
        assert connection.execute(text("SELECT COUNT(*) FROM audit_events WHERE action IN ('create_connection','update_connection')")).scalar_one()==2
    store.close()


def test_target_grants_and_explicit_denies_apply_before_registration_and_reads(tmp_path):
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    other=work.create_project(actor,'Other','urn:connections-other:')
    with pytest.raises(Exception) as denied: service.create(actor,other.project_id,'Denied','db')
    assert denied.value.code=='FORBIDDEN'
    item=service.create(actor,project.project_id,'Allowed','db')
    with pytest.raises(Exception) as cross: service.get(actor,other.project_id,item.connection_id)
    assert cross.value.code=='CONNECTION_NOT_FOUND'
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO permission_denies(user_id,project_id,action) VALUES(:user,:project,'*')"),{'user':actor.user_id,'project':project.project_id})
    with pytest.raises(Exception) as denied_read: service.get(actor,project.project_id,item.connection_id)
    assert denied_read.value.code=='FORBIDDEN'
    with pytest.raises(Exception): service.create(actor,project.project_id,'Denied','db')
    store.close()


def test_unknown_alias_changed_target_binding_and_unsafe_names_fail_closed(tmp_path):
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    with pytest.raises(Exception) as unknown: service.create(actor,project.project_id,'Unknown','not-present')
    assert unknown.value.code=='INVALID_CONNECTION'
    with pytest.raises(Exception) as unsafe: service.create(actor,project.project_id,'https://safe.invalid https://x:NONLIVE-MARKER@other.invalid','db')
    assert unsafe.value.code=='INVALID_CONNECTION' and 'NONLIVE-MARKER' not in str(unsafe.value)
    item=service.create(actor,project.project_id,'Source','db')
    second=tmp_path/'second.db'; second.write_bytes(path.read_bytes()); second.chmod(0o600)
    changed=domain.TargetRegistry({'db':domain.Target('db','sqlite',str(second))},{'db':{project.project_id}})
    changed_service=module.ConnectionService(store,accounts,changed)
    with pytest.raises(Exception) as bad_binding: changed_service.get(actor,project.project_id,item.connection_id)
    assert bad_binding.value.code=='TARGET_CHANGED'
    refreshed=changed_service.update(actor,project.project_id,item.connection_id,item.revision,'Refreshed','db')
    assert changed_service.get(actor,project.project_id,item.connection_id)==refreshed
    store.close()


@pytest.mark.parametrize('url',['http://outside.invalid','https://localhost','https://127.0.0.1','https://[::ffff:127.0.0.1]','https://user:NONLIVE@outside.invalid','https://outside.invalid?access_token=NONLIVE','https://outside.invalid#fragment'])
def test_operator_http_configuration_rejects_unsafe_targets_without_network(tmp_path,url):
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    with pytest.raises(ValueError): domain.TargetRegistry({'remote':domain.Target('remote','http',url)},{'remote':{project.project_id}})
    store.close()


def test_alias_and_grants_are_immutable_and_sqlite_targets_reject_symlinks(tmp_path):
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    grant={project.project_id}; mapping={'db':domain.Target('db','sqlite',str(path))}
    targets=domain.TargetRegistry(mapping,{'db':grant})
    grant.clear(); mapping.clear()
    assert targets.resolve('db',project.project_id).alias=='db'
    link=tmp_path/'link.db'; link.symlink_to(path)
    with pytest.raises(ValueError): domain.TargetRegistry({'db':domain.Target('db','sqlite',str(link))},{'db':{project.project_id}})
    store.close()


def test_authenticated_http_connection_crud_uses_only_operator_aliases(tmp_path):
    import asyncio
    from test_api import ORIGIN,client,login
    from test_accounts import TestSecrets
    service,work,accounts,store,actor,project,path,domain,module=setup(tmp_path)
    from ontology_platform.api.app import create_app
    app=create_app(store,work.sources.root,TestSecrets(),[ORIGIN],connection_targets=service.targets)
    async def run():
        async with await client(app) as c:
            endpoint=f'/api/projects/{project.project_id}/connections'
            assert (await c.get(endpoint)).status_code==401
            await login(c)
            created=await c.post(endpoint,json={'name':'Source','target_alias':'db'})
            assert created.status_code==201
            value=created.json(); assert value['status']=='CONFIGURED' and str(path) not in created.text
            assert (await c.get(endpoint)).json()==[value]
            assert (await c.get(endpoint+'/'+value['connection_id'])).json()==value
            updated=await c.put(endpoint+'/'+value['connection_id'],json={'base_revision':value['revision'],'name':'Updated','target_alias':'db'})
            assert updated.status_code==200 and updated.json()['revision']!=value['revision']
            stale=await c.put(endpoint+'/'+value['connection_id'],json={'base_revision':value['revision'],'name':'Old','target_alias':'db'})
            assert stale.status_code==409 and stale.json()['code']=='STALE_REVISION'
            unsafe=await c.post(endpoint,json={'name':'Rejected','target_alias':'db','locator':str(path),'credential_ref':'env:ONTOLOGY_SECRET_OUTSIDE'})
            assert unsafe.status_code==422 and str(path) not in unsafe.text
            unknown=await c.post(endpoint,json={'name':'Rejected','target_alias':'arbitrary'})
            assert unknown.status_code==400 and unknown.json()['code']=='INVALID_CONNECTION'
    asyncio.run(run()); store.close()


def test_default_http_composition_does_not_grant_any_operator_targets(tmp_path):
    import asyncio
    from test_api import api,client,login
    app,store,root=api(tmp_path)
    async def run():
        async with await client(app) as c:
            await login(c)
            pid=(await c.post('/api/projects',json={'name':'Technical','namespace':'urn:no-targets:'})).json()['project_id']
            endpoint=f'/api/projects/{pid}/connections'
            assert (await c.get(endpoint)).json()==[]
            response=await c.post(endpoint,json={'name':'No target','target_alias':'db'})
            assert response.status_code==400 and response.json()['code']=='INVALID_CONNECTION'
    asyncio.run(run()); store.close()
