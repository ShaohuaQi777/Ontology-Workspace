"""Local account/session authorization; no HTTP or semantic engine implementation."""
from dataclasses import dataclass,field
import hashlib,hmac,json,re,secrets,time,uuid
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.infrastructure.account_schema import initialize_account_schema

PERMISSIONS={
    'read':{'engineer','consultant','expert','admin','owner'},
    'edit':{'engineer','consultant','owner'},
    'review':{'engineer','consultant','owner'},
    'certify':{'expert'},
    'approve_release':{'owner'},
    'deploy':{'admin'},
    'manage_members':{'admin','owner'},
}


@dataclass(frozen=True)
class UserSummary:
    user_id:str
    username:str
    global_role:str


@dataclass(frozen=True)
class Principal(UserSummary):
    _session_hash:str=field(repr=False)
    _proof:str=field(repr=False)


class AccountService:
    def __init__(self,store,secret_provider,clock=time.time):
        self.store=store; self.secret_provider=secret_provider; self.clock=clock
        self._principal_key=secrets.token_bytes(32)

    def initialize(self): initialize_account_schema(self.store)

    @staticmethod
    def _username(username):
        if not isinstance(username,str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,63}',username):
            raise ServiceError('INVALID_ACCOUNT')
        return username

    def _password(self,reference):
        try: value=self.secret_provider.resolve(reference)
        except Exception: raise ServiceError('SECRET_UNAVAILABLE') from None
        if not isinstance(value,SecretStr): raise ServiceError('SECRET_UNAVAILABLE')
        material=value.get_secret_value().encode()
        if not 12<=len(material)<=256: raise ServiceError('INVALID_ACCOUNT')
        return material

    @staticmethod
    def _hash_password(material,salt): return hashlib.pbkdf2_hmac('sha256',material,salt,600000)

    def _audit(self,connection,actor,action,resource,outcome):
        connection.execute(text('INSERT INTO audit_events(actor_id,action,resource_id,outcome,created_at) VALUES(:actor,:action,:resource,:outcome,:now)'),{'actor':actor,'action':action,'resource':resource,'outcome':outcome,'now':int(self.clock())})

    def _create(self,connection,username,material,global_role):
        salt=secrets.token_bytes(16); user_id=str(uuid.uuid4())
        connection.execute(text('INSERT INTO accounts(id,username,password_hash,salt,global_role) VALUES(:id,:username,:hash,:salt,:role)'),{'id':user_id,'username':username,'hash':self._hash_password(material,salt),'salt':salt,'role':global_role})
        return UserSummary(user_id,username,global_role)

    def bootstrap_admin(self,username,password_ref):
        self._username(username)
        # Check before resolving a secret; guard insert below also closes concurrent bootstraps.
        with self.store.transaction() as connection:
            if connection.execute(text('SELECT COUNT(*) FROM accounts')).scalar_one(): raise ServiceError('BOOTSTRAP_DISABLED')
        material=self._password(password_ref)
        try:
            with self.store.transaction() as connection:
                connection.execute(text('INSERT INTO account_bootstrap VALUES(1)'))
                user=self._create(connection,username,material,'admin')
                self._audit(connection,user.user_id,'bootstrap',user.user_id,'succeeded')
        except IntegrityError: raise ServiceError('BOOTSTRAP_DISABLED') from None
        return user

    def _proof(self,user_id,username,role,digest):
        payload=json.dumps([user_id,username,role,digest],separators=(',',':')).encode()
        return hmac.new(self._principal_key,payload,'sha256').hexdigest()

    @staticmethod
    def _digest(secret):
        if not isinstance(secret,SecretStr): raise ServiceError('UNAUTHENTICATED')
        raw=secret.get_secret_value()
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',raw): raise ServiceError('UNAUTHENTICATED')
        return hashlib.sha256(raw.encode()).hexdigest()

    def _session(self,connection,digest):
        row=connection.execute(text('SELECT a.id,a.username,a.global_role FROM sessions s JOIN accounts a ON a.id=s.user_id WHERE s.digest=:digest AND s.revoked=0 AND s.expires_at>:now AND a.disabled=0'),{'digest':digest,'now':int(self.clock())}).mappings().first()
        if row is None: raise ServiceError('UNAUTHENTICATED')
        return row

    def resolve_session(self,secret):
        digest=self._digest(secret)
        with self.store.transaction() as connection: row=self._session(connection,digest)
        return Principal(row['id'],row['username'],row['global_role'],digest,self._proof(row['id'],row['username'],row['global_role'],digest))

    def open_single_user_session(self,username='workspace'):
        """Create a server-owned local identity for explicit loopback demo mode."""
        self._username(username); now=int(self.clock()); secret=SecretStr(secrets.token_urlsafe(32)); digest=self._digest(secret)
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            row=connection.execute(text('SELECT id,global_role,disabled FROM accounts WHERE username=:username'),{'username':username}).mappings().first()
            if row is None:
                user=self._create(connection,username,secrets.token_bytes(32),'admin'); user_id=user.user_id
                self._audit(connection,user_id,'single_user_bootstrap',user_id,'succeeded')
            else:
                if row['disabled'] or row['global_role']!='admin': raise ServiceError('INVALID_ACCOUNT')
                user_id=row['id']
            for project_id in connection.execute(text('SELECT id FROM projects')).scalars():
                for role in ('owner','expert','admin','engineer'):
                    connection.execute(text('INSERT OR IGNORE INTO memberships(user_id,project_id,role) VALUES(:user,:project,:role)'),{'user':user_id,'project':project_id,'role':role})
            connection.execute(text('INSERT INTO sessions(digest,user_id,expires_at) VALUES(:digest,:user,:expires)'),{'digest':digest,'user':user_id,'expires':now+28800})
            self._audit(connection,user_id,'single_user_session',user_id,'succeeded')
        return self.resolve_session(secret)

    def _actor(self,connection,actor):
        if not isinstance(actor,Principal): raise ServiceError('UNAUTHENTICATED')
        expected=self._proof(actor.user_id,actor.username,actor.global_role,actor._session_hash)
        if not hmac.compare_digest(expected,actor._proof): raise ServiceError('UNAUTHENTICATED')
        row=self._session(connection,actor._session_hash)
        if row['id']!=actor.user_id: raise ServiceError('UNAUTHENTICATED')
        return row

    def create_user(self,actor,username,password_ref):
        self._username(username)
        with self.store.transaction() as connection:
            user=self._actor(connection,actor)
            if user['global_role']!='admin': raise ServiceError('FORBIDDEN')
        material=self._password(password_ref)
        try:
            with self.store.transaction() as connection:
                if self._actor(connection,actor)['global_role']!='admin': raise ServiceError('FORBIDDEN')
                created=self._create(connection,username,material,'member')
                self._audit(connection,actor.user_id,'create_user',created.user_id,'succeeded')
        except IntegrityError: raise ServiceError('ACCOUNT_EXISTS') from None
        return created

    def login(self,username,password):
        self._username(username)
        if not isinstance(password,SecretStr) or len(password.get_secret_value().encode())>256:
            raise ServiceError('AUTHENTICATION_FAILED')
        subject=hashlib.sha256(username.encode()).hexdigest(); now=int(self.clock())
        failure=False; session=None
        with self.store.transaction() as connection:
            # SQLite legacy SELECT does not begin a write transaction: reserve the
            # writer before checking the persisted budget, including across processes.
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            attempts=connection.execute(text('SELECT attempts,window_start FROM login_failures WHERE subject=:subject'),{'subject':subject}).mappings().first()
            if attempts and now-attempts['window_start']>=300:
                connection.execute(text('DELETE FROM login_failures WHERE subject=:subject'),{'subject':subject}); attempts=None
            if attempts and attempts['attempts']>=5: raise ServiceError('LOGIN_RATE_LIMIT')
            user=connection.execute(text('SELECT * FROM accounts WHERE username=:username'),{'username':username}).mappings().first()
            salt=user['salt'] if user else b'\0'*16
            digest=self._hash_password(password.get_secret_value().encode(),salt)
            matched=hmac.compare_digest(digest,user['password_hash'] if user else b'\0'*32)
            if not user or user['disabled'] or not matched:
                connection.execute(text('INSERT INTO login_failures(subject,window_start,attempts) VALUES(:subject,:now,1) ON CONFLICT(subject) DO UPDATE SET attempts=login_failures.attempts+1'),{'subject':subject,'now':now})
                self._audit(connection,user['id'] if user else None,'login',None,'failed'); failure=True
            else:
                connection.execute(text('DELETE FROM login_failures WHERE subject=:subject'),{'subject':subject})
                session=SecretStr(secrets.token_urlsafe(32))
                connection.execute(text('INSERT INTO sessions(digest,user_id,expires_at) VALUES(:digest,:user,:expires)'),{'digest':self._digest(session),'user':user['id'],'expires':now+28800})
                self._audit(connection,user['id'],'login',None,'succeeded')
        # Failed-attempt/audit writes must commit, not roll back with the public error.
        if failure: raise ServiceError('AUTHENTICATION_FAILED')
        return session

    def revoke_session(self,secret):
        digest=self._digest(secret)
        with self.store.transaction() as connection:
            row=self._session(connection,digest)
            connection.execute(text('UPDATE sessions SET revoked=1 WHERE digest=:digest'),{'digest':digest})
            self._audit(connection,row['id'],'logout',None,'succeeded')

    def set_member(self,actor,project_id,user_id,role):
        if role not in {'engineer','consultant','expert','admin','owner'}: raise ServiceError('FORBIDDEN')
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.require_project(actor,project_id,'manage_members')
            if connection.execute(text('SELECT 1 FROM accounts WHERE id=:user AND disabled=0'),{'user':user_id}).first() is None: raise ServiceError('INVALID_ACCOUNT')
            connection.execute(text('INSERT OR IGNORE INTO memberships(user_id,project_id,role) VALUES(:user,:project,:role)'),{'user':user_id,'project':project_id,'role':role})
            self._audit(connection,actor.user_id,'set_member',project_id,'succeeded')

    def remove_member(self,actor,project_id,user_id,role):
        if role not in {'engineer','consultant','expert','admin','owner'}: raise ServiceError('FORBIDDEN')
        with self.store.transaction() as connection:
            connection.exec_driver_sql('BEGIN IMMEDIATE')
            self.require_project(actor,project_id,'manage_members')
            connection.execute(text('DELETE FROM memberships WHERE user_id=:user AND project_id=:project AND role=:role'),{'user':user_id,'project':project_id,'role':role})
            self._audit(connection,actor.user_id,'remove_member',project_id,'succeeded')

    def require_project(self,actor,project_id,action):
        with self.store.transaction() as connection:
            user=self._actor(connection,actor)
            if action not in PERMISSIONS: raise ServiceError('FORBIDDEN')
            exists=connection.execute(text('SELECT 1 FROM projects WHERE id=:project'),{'project':project_id}).first()
            if not exists: raise ServiceError('FORBIDDEN')
            denied=connection.execute(text('SELECT 1 FROM permission_denies WHERE user_id=:user AND project_id=:project AND action IN (:action,\'*\')'),{'user':user['id'],'project':project_id,'action':action}).first()
            if denied: raise ServiceError('FORBIDDEN')
            roles=set(connection.execute(text('SELECT role FROM memberships WHERE user_id=:user AND project_id=:project'),{'user':user['id'],'project':project_id}).scalars())
            if user['global_role']=='admin': roles.add('admin')
            if not roles&PERMISSIONS[action]: raise ServiceError('FORBIDDEN')
