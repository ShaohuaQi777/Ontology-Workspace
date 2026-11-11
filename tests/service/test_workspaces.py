"""Real scoped revisions and source artifacts, not business scenario fixtures."""
import hashlib,importlib,json,os
import pytest
from sqlalchemy import text
from pydantic import SecretStr
from test_accounts import service,principal,PASSWORD


def workspace(tmp_path):
    accounts,store,clock=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    root=tmp_path/'artifacts'; root.mkdir(mode=0o700)
    cls=importlib.import_module('ontology_platform.application.workspaces').WorkspaceService
    work=cls(store,accounts,root); work.initialize()
    return work,accounts,store,principal(accounts),root


def test_project_namespace_unique_and_owner_membership(tmp_path):
    work,accounts,store,actor,_=workspace(tmp_path)
    project=work.create_project(actor,'技术工作区','https://example.invalid/tools/')
    assert project.workspace_revision=='w0'
    accounts.require_project(actor,project.project_id,'approve_release')
    with pytest.raises(Exception) as duplicate: work.create_project(actor,'Other','https://example.invalid/tools/')
    assert duplicate.value.code=='NAMESPACE_CONFLICT'
    with pytest.raises(Exception) as credentials: work.create_project(actor,'Unsafe','https://alice:TECHNICAL-MARKER@example.invalid/')
    assert credentials.value.code=='INVALID_WORKSPACE' and 'TECHNICAL-MARKER' not in str(credentials.value)
    store.close()


def test_revision_cas_immutable_and_dependency_change_draft(tmp_path):
    work,accounts,store,actor,_=workspace(tmp_path); project=work.create_project(actor,'Technical','urn:technical:')
    first=work.save_layer(actor,project.project_id,'tbox','w0',{'classes':['Node']},{})
    assert first.state=='DRAFT'
    with pytest.raises(Exception) as stale: work.save_layer(actor,project.project_id,'tbox','w0',{'classes':['Other']},{})
    assert stale.value.code=='STALE_REVISION'
    next_=work.save_layer(actor,project.project_id,'abox',first.revision_id,{'state':'CERTIFIED'},{'tbox':first.revision_id})
    assert next_.state=='DRAFT' and next_.dependencies=={'tbox':first.revision_id}
    restored=work.read_revision(actor,project.project_id,first.revision_id)
    assert restored.content=={'classes':['Node']} and restored.sha256==first.sha256
    assert restored.revision_id!=next_.revision_id
    raw=json.dumps({'content':{'classes':['Node']},'dependencies':{}},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    assert restored.sha256==hashlib.sha256(raw).hexdigest()
    store.close()


def test_cross_project_revision_and_source_references_rejected(tmp_path):
    work,accounts,store,actor,_=workspace(tmp_path)
    one=work.create_project(actor,'One','urn:one:'); two=work.create_project(actor,'Two','urn:two:')
    revision=work.save_layer(actor,one.project_id,'tbox','w0',{'classes':[]},{})
    with pytest.raises(Exception) as bad: work.save_layer(actor,two.project_id,'abox','w0',{}, {'tbox':revision.revision_id})
    assert bad.value.code=='INVALID_DEPENDENCY'
    source=work.register_source(actor,one.project_id,'csv',b'id,value\nn1,7\n')
    with pytest.raises(Exception) as bad: work.read_source(actor,two.project_id,source.source_id)
    assert bad.value.code=='INVALID_SOURCE'
    store.close()


def test_non_member_cannot_write_read_revision_or_source(tmp_path):
    work,accounts,store,actor,_=workspace(tmp_path); project=work.create_project(actor,'One','urn:one:')
    revision=work.save_layer(actor,project.project_id,'tbox','w0',{},{}); source=work.register_source(actor,project.project_id,'text',b'technical')
    accounts.create_user(actor,'outsider','test:password'); outsider=principal(accounts,'outsider')
    for action in [lambda:work.save_layer(outsider,project.project_id,'tbox',revision.revision_id,{},{}),lambda:work.read_revision(outsider,project.project_id,revision.revision_id),lambda:work.read_source(outsider,project.project_id,source.source_id)]:
        with pytest.raises(Exception) as denied: action()
        assert denied.value.code=='FORBIDDEN'
    store.close()


@pytest.mark.parametrize('format,data',[('json',b'{"client_secret":"TECHNICAL-MARKER"}'),('json',b'{"url":"https://a:TECHNICAL-MARKER@example.invalid"}'),('text',b'https://a:TECHNICAL-MARKER@example.invalid'),('text',b'x'*1048577),('../pdf',b'technical')])
def test_source_preflight_rejects_before_any_artifact_persistence(tmp_path,format,data):
    work,accounts,store,actor,root=workspace(tmp_path); project=work.create_project(actor,'One','urn:one:')
    before=set(root.rglob('*'))
    with pytest.raises(Exception) as bad: work.register_source(actor,project.project_id,format,data)
    assert bad.value.code=='INVALID_SOURCE' and 'TECHNICAL-MARKER' not in str(bad.value)
    assert set(root.rglob('*'))==before
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM sources')).scalar_one()==0
    store.close()


def test_source_hash_and_symlink_checked_and_private_modes(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path); project=work.create_project(actor,'One','urn:one:')
    source=work.register_source(actor,project.project_id,'csv',b'id,value\nn1,7\n')
    assert source.sha256==hashlib.sha256(b'id,value\nn1,7\n').hexdigest()
    assert work.read_source(actor,project.project_id,source.source_id)==b'id,value\nn1,7\n'
    path=next(p for p in root.rglob('*') if p.is_file()); assert path.stat().st_mode&0o777==0o600
    path.write_bytes(b'wrong')
    with pytest.raises(Exception) as corrupt: work.read_source(actor,project.project_id,source.source_id)
    assert corrupt.value.code=='INVALID_SOURCE'
    # Replace only our controlled test file with a symlink to a technical owned file.
    target=tmp_path/'target'; target.write_bytes(b'id,value\nn1,7\n')
    assert path.resolve().is_relative_to(root.resolve()) and path.name not in ('metadata.db','target')
    path.unlink(); path.symlink_to(target)
    with pytest.raises(Exception) as symlink: work.read_source(actor,project.project_id,source.source_id)
    assert symlink.value.code=='INVALID_SOURCE'
    store.close()


def test_workspace_and_sources_survive_reopen(tmp_path):
    work,accounts,store,actor,root=workspace(tmp_path); project=work.create_project(actor,'One','urn:one:')
    revision=work.save_layer(actor,project.project_id,'rules','w0',{'rules':[]},{})
    source=work.register_source(actor,project.project_id,'json',b'{"id":"n1"}')
    store.close(); accounts,store,_=service(tmp_path); actor=principal(accounts)
    work=importlib.import_module('ontology_platform.application.workspaces').WorkspaceService(store,accounts,root); work.initialize()
    assert work.read_revision(actor,project.project_id,revision.revision_id).content=={'rules':[]}
    assert work.read_source(actor,project.project_id,source.source_id)==b'{"id":"n1"}'
    store.close()


def test_artifact_root_must_not_include_metadata_database(tmp_path):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    cls=importlib.import_module('ontology_platform.application.workspaces').WorkspaceService
    with pytest.raises(ValueError): cls(store,accounts,tmp_path)
    store.close()
