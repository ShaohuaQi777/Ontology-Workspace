"""Revision-bound expert evidence primitives, not expert business correctness claims."""
import pytest
from sqlalchemy import text
from test_workspaces import workspace
from test_accounts import principal


def test_expert_evidence_binds_revision_and_is_not_inherited_by_new_draft(tmp_path):
    work,accounts,store,owner,_=workspace(tmp_path); project=work.create_project(owner,'Technical','urn:certification:')
    revision=work.save_layer(owner,project.project_id,'tbox','w0',{'classes':['Node']},{})
    with pytest.raises(Exception) as non_expert: work.record_certification(owner,project.project_id,revision.revision_id,{'review':'technical'})
    assert non_expert.value.code=='FORBIDDEN'
    user=accounts.create_user(owner,'expert','test:password')
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO memberships VALUES(:user,:project,'expert')"),{'user':user.user_id,'project':project.project_id})
    expert=principal(accounts,'expert')
    record=work.record_certification(expert,project.project_id,revision.revision_id,{'review':'technical'})
    assert record.revision_id==revision.revision_id
    assert record.evidence=={'review':'technical'}
    with store.transaction() as connection:
        import json
        stored=connection.execute(text('SELECT evidence_json FROM certification_records WHERE id=:id'),{'id':record.record_id}).scalar_one()
        assert json.loads(stored)=={'review':'technical'}
    assert work.read_revision(owner,project.project_id,revision.revision_id).state=='CERTIFIED'
    changed=work.save_layer(owner,project.project_id,'tbox',revision.revision_id,{'classes':['Node','Other']},{})
    assert changed.state=='DRAFT'
    with pytest.raises(Exception) as stale: work.record_certification(expert,project.project_id,revision.revision_id,{'review':'technical'})
    assert stale.value.code=='STALE_REVISION'
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM certification_records')).scalar_one()==1
    store.close()


def test_dependency_revision_change_invalidates_effective_certification(tmp_path):
    work,accounts,store,owner,_=workspace(tmp_path); project=work.create_project(owner,'Technical','urn:deps:')
    tbox=work.save_layer(owner,project.project_id,'tbox','w0',{'classes':['Node']},{})
    abox=work.save_layer(owner,project.project_id,'abox',tbox.revision_id,{'entities':[]},{'tbox':tbox.revision_id})
    user=accounts.create_user(owner,'expert','test:password')
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO memberships VALUES(:user,:project,'expert')"),{'user':user.user_id,'project':project.project_id})
    expert=principal(accounts,'expert'); work.record_certification(expert,project.project_id,abox.revision_id,{'review':'technical'})
    work.save_layer(owner,project.project_id,'tbox',abox.revision_id,{'classes':['Node','Other']},{})
    assert work.read_revision(owner,project.project_id,abox.revision_id).state=='DRAFT'
    with pytest.raises(Exception) as stale: work.record_certification(expert,project.project_id,abox.revision_id,{'review':'technical'})
    assert stale.value.code=='STALE_REVISION'
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM certification_records')).scalar_one()==1
    store.close()
