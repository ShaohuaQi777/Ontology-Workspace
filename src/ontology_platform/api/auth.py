"""Cookie-only transient session resolution; client role/user headers never read."""
from fastapi import Request
from pydantic import SecretStr

COOKIE='ontology_session'


def actor(request:Request):
    if single_user:=getattr(request.app.state,'single_user_actor',None): return single_user
    return request.app.state.accounts.resolve_session(SecretStr(request.cookies.get(COOKIE,'')))
