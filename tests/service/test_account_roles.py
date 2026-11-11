"""Project expert, owner and admin decisions stay independent from login identity."""
import pytest
from sqlalchemy import text
from test_accounts import service,principal,seed_project


@pytest.mark.parametrize('role,allowed,denied',[
    ('engineer','edit','certify'),('consultant','review','deploy'),
    ('expert','certify','approve_release'),('owner','approve_release','certify'),
    ('admin','deploy','certify'),
])
def test_project_role_only_grants_its_governance_action(tmp_path,role,allowed,denied):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    user=accounts.create_user(principal(accounts),'member','test:password'); actor=principal(accounts,'member')
    seed_project(store,user.user_id,role=role)
    accounts.require_project(actor,'p1',allowed)
    with pytest.raises(Exception) as rejected: accounts.require_project(actor,'p1',denied)
    assert rejected.value.code=='FORBIDDEN'
    store.close()


def test_global_admin_cannot_implicitly_expert_certify_or_override_explicit_deny(tmp_path):
    accounts,store,_=service(tmp_path); root=accounts.bootstrap_admin('root','test:password'); actor=principal(accounts)
    seed_project(store,root.user_id,role='admin')
    with pytest.raises(Exception) as certify: accounts.require_project(actor,'p1','certify')
    assert certify.value.code=='FORBIDDEN'
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO permission_denies(user_id,project_id,action) VALUES(:user,'p1','*')"),{'user':root.user_id})
    with pytest.raises(Exception) as deploy: accounts.require_project(actor,'p1','deploy')
    assert deploy.value.code=='FORBIDDEN'
    store.close()
