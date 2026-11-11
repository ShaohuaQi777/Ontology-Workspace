"""Controlled actual concurrent local logins; derivation/SQLite are not replaced."""
from concurrent.futures import ThreadPoolExecutor
import threading
from pydantic import SecretStr
from sqlalchemy import text
from test_accounts import service,PASSWORD


def test_last_allowed_failure_slot_not_spent_by_two_concurrent_logins(tmp_path,monkeypatch):
    accounts,store,_=service(tmp_path); accounts.bootstrap_admin('root','test:password')
    for _ in range(4):
        try: accounts.login('root',SecretStr('TECHNICAL-WRONG-MATERIAL'))
        except Exception as error: assert error.code=='AUTHENTICATION_FAILED'
    derive=accounts._hash_password; gate=threading.Barrier(2)
    def concurrent_derivation(material,salt):
        value=derive(material,salt)
        try: gate.wait(timeout=0.3)
        except threading.BrokenBarrierError: pass
        return value
    monkeypatch.setattr(accounts,'_hash_password',concurrent_derivation)
    def attempt():
        try: accounts.login('root',SecretStr('TECHNICAL-WRONG-MATERIAL'))
        except Exception as error: return getattr(error,'code',type(error).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(lambda _:attempt(),range(2)))
    assert sorted(outcomes)==['AUTHENTICATION_FAILED','LOGIN_RATE_LIMIT']
    with store.transaction() as connection: assert connection.execute(text('SELECT attempts FROM login_failures')).scalar_one()==5
    store.close()
