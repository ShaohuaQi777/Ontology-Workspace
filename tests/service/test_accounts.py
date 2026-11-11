"""Real local password hashing/session metadata/RBAC with technical test credentials."""
import importlib,dataclasses
import pytest
from pydantic import SecretStr
from sqlalchemy import text
from ontology_platform.infrastructure.metadata import MetadataStore

PASSWORD='TECHNICAL-TEST-MATERIAL-NOT-A-LIVE-CREDENTIAL'


class TestSecrets:
    __test__=False
    def resolve(self,reference):
        if reference!='test:password': raise RuntimeError('TECHNICAL-PRIVATE-MARKER')
        return SecretStr(PASSWORD)


class Clock:
    def __init__(self): self.now=1000
    def __call__(self): return self.now


def service(tmp_path):
    module=importlib.import_module('ontology_platform.application.accounts')
    store=MetadataStore('sqlite:///'+str(tmp_path/'metadata.db')); store.initialize()
    clock=Clock(); accounts=module.AccountService(store,TestSecrets(),clock)
    accounts.initialize()
    return accounts,store,clock


def principal(accounts,username='root'):
    return accounts.resolve_session(accounts.login(username,SecretStr(PASSWORD)))


def seed_project(store,user_id,role='engineer',project='p1'):
    with store.transaction() as connection:
        connection.execute(text('INSERT OR IGNORE INTO projects(id,name,namespace,owner_id,workspace_revision) VALUES(:id,:name,:namespace,:owner,:revision)'),{'id':project,'name':project,'namespace':'urn:project:'+project+':','owner':user_id,'revision':'w0'})
        connection.execute(text('INSERT INTO memberships(user_id,project_id,role) VALUES(:user,:project,:role)'),{'user':user_id,'project':project,'role':role})


def test_password_and_session_only_hashes_persist_and_reopen(tmp_path):
    accounts,store,clock=service(tmp_path)
    user=accounts.bootstrap_admin('root','test:password')
    secret=accounts.login('root',SecretStr(PASSWORD)); actor=accounts.resolve_session(secret)
    assert PASSWORD not in repr(user)+repr(secret)+repr(actor)
    with store.transaction() as connection:
        row=connection.execute(text('SELECT password_hash,salt FROM accounts WHERE id=:id'),{'id':user.user_id}).one()
        assert len(row.password_hash)==32 and len(row.salt)==16
        assert row.password_hash!=PASSWORD.encode()
        import hashlib
        assert row.password_hash==hashlib.pbkdf2_hmac('sha256',PASSWORD.encode(),row.salt,600000)
        assert connection.execute(text('SELECT COUNT(*) FROM sessions')).scalar_one()==1
    raw=secret.get_secret_value(); store.close()
    assert PASSWORD.encode() not in (tmp_path/'metadata.db').read_bytes()
    assert raw.encode() not in (tmp_path/'metadata.db').read_bytes()
    accounts,store,_=service(tmp_path)
    assert accounts.resolve_session(SecretStr(raw)).user_id==user.user_id
    store.close()


def test_wrong_expired_revoked_and_disabled_sessions_denied(tmp_path):
    accounts,store,clock=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    with pytest.raises(Exception) as wrong: accounts.login('root',SecretStr('TECHNICAL-WRONG-MATERIAL'))
    assert wrong.value.code=='AUTHENTICATION_FAILED'
    secret=accounts.login('root',SecretStr(PASSWORD)); clock.now+=8*60*60
    with pytest.raises(Exception) as expired: accounts.resolve_session(secret)
    assert expired.value.code=='UNAUTHENTICATED'
    clock.now=1000; secret=accounts.login('root',SecretStr(PASSWORD)); accounts.revoke_session(secret)
    with pytest.raises(Exception) as revoked: accounts.resolve_session(secret)
    assert revoked.value.code=='UNAUTHENTICATED'
    secret=accounts.login('root',SecretStr(PASSWORD))
    with store.transaction() as connection: connection.execute(text("UPDATE accounts SET disabled=1 WHERE username='root'"))
    with pytest.raises(Exception) as disabled: accounts.resolve_session(secret)
    assert disabled.value.code=='UNAUTHENTICATED'
    store.close()


def test_missing_account_wrong_password_same_failure_code(tmp_path):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    for username in ['root','missing']:
        with pytest.raises(Exception) as caught: accounts.login(username,SecretStr('TECHNICAL-WRONG-MATERIAL'))
        assert caught.value.code=='AUTHENTICATION_FAILED'
        assert PASSWORD not in str(caught.value)
    store.close()


def test_bootstrap_not_reusable_and_secrets_fail_closed(tmp_path):
    accounts,store,_=service(tmp_path)
    with pytest.raises(Exception) as missing: accounts.bootstrap_admin('root','test:missing')
    assert missing.value.code=='SECRET_UNAVAILABLE'
    assert 'TECHNICAL-PRIVATE-MARKER' not in str(missing.value)
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM accounts')).scalar_one()==0
    accounts.bootstrap_admin('root','test:password')
    with pytest.raises(Exception) as twice: accounts.bootstrap_admin('another','test:password')
    assert twice.value.code=='BOOTSTRAP_DISABLED'
    store.close()


def test_rate_limit_survives_restart_and_expires(tmp_path):
    accounts,store,clock=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    for _ in range(5):
        with pytest.raises(Exception) as failed: accounts.login('root',SecretStr('TECHNICAL-WRONG-MATERIAL'))
        assert failed.value.code=='AUTHENTICATION_FAILED'
    store.close(); accounts,store,clock=service(tmp_path)
    with pytest.raises(Exception) as limited: accounts.login('root',SecretStr(PASSWORD))
    assert limited.value.code=='LOGIN_RATE_LIMIT'
    clock.now+=300
    assert accounts.resolve_session(accounts.login('root',SecretStr(PASSWORD))).username=='root'
    store.close()


def test_fake_principal_and_mutated_role_not_accepted(tmp_path):
    accounts,store,_=service(tmp_path); root=accounts.bootstrap_admin('root','test:password')
    actor=principal(accounts); user=accounts.create_user(actor,'member','test:password')
    member=principal(accounts,'member'); seed_project(store,user.user_id)
    with pytest.raises(Exception) as forged:
        accounts.require_project(dataclasses.replace(member,user_id=root.user_id,global_role='admin'),'p1','deploy')
    assert forged.value.code=='UNAUTHENTICATED'
    with pytest.raises(Exception) as no_admin: accounts.create_user(member,'intruder','test:password')
    assert no_admin.value.code=='FORBIDDEN'
    store.close()


def test_cross_project_unknown_action_and_explicit_deny_fail(tmp_path):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    user=accounts.create_user(principal(accounts),'member','test:password'); actor=principal(accounts,'member')
    seed_project(store,user.user_id)
    assert accounts.require_project(actor,'p1','edit') is None
    for project,action in [('p2','read'),('p1','unknown'),('p1','certify'),('p1','approve_release'),('p1','deploy')]:
        with pytest.raises(Exception) as denied: accounts.require_project(actor,project,action)
        assert denied.value.code=='FORBIDDEN'
    with store.transaction() as connection:
        connection.execute(text("INSERT INTO permission_denies(user_id,project_id,action) VALUES(:user,'p1','edit')"),{'user':user.user_id})
    with pytest.raises(Exception) as denied: accounts.require_project(actor,'p1','edit')
    assert denied.value.code=='FORBIDDEN'
    store.close()


def test_revoke_after_principal_resolution_invalidates_authorization(tmp_path):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    secret=accounts.login('root',SecretStr(PASSWORD)); actor=accounts.resolve_session(secret)
    seed_project(store,actor.user_id,role='admin')
    accounts.revoke_session(secret)
    with pytest.raises(Exception) as denied: accounts.require_project(actor,'p1','read')
    assert denied.value.code=='UNAUTHENTICATED'
    store.close()


@pytest.mark.parametrize('username',['','BAD NAME','../root','https://a:b@example.invalid','a'*65])
def test_invalid_usernames_rejected_before_account_persistence(tmp_path,username):
    accounts,store,_=service(tmp_path)
    with pytest.raises(Exception) as caught: accounts.bootstrap_admin(username,'test:password')
    assert caught.value.code=='INVALID_ACCOUNT'
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM accounts')).scalar_one()==0
    store.close()


def test_environment_secret_provider_resolves_only_allowlisted_refs():
    module=importlib.import_module('ontology_platform.infrastructure.secrets')
    provider=module.EnvironmentSecretProvider({'env:ONTOLOGY_SECRET_TEST'},{'ONTOLOGY_SECRET_TEST':PASSWORD,'OTHER_PRIVATE':PASSWORD})
    assert provider.resolve('env:ONTOLOGY_SECRET_TEST').get_secret_value()==PASSWORD
    for reference in ['env:OTHER_PRIVATE','env:MISSING','raw:'+PASSWORD,'env:../OTHER_PRIVATE']:
        with pytest.raises(Exception) as caught: provider.resolve(reference)
        assert caught.value.code=='SECRET_UNAVAILABLE' and PASSWORD not in str(caught.value)
