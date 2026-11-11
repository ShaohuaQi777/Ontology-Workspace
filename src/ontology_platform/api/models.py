"""Bounded public JSON DTOs, without user identity headers or credential echoes."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,JsonValue,SecretStr


class Model(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class Login(Model):
    username:str=Field(min_length=1,max_length=64)
    password:SecretStr


class AccountCreate(Model):
    username:str=Field(min_length=1,max_length=64)
    password_ref:str=Field(min_length=1,max_length=256)


class ProjectCreate(Model):
    name:str=Field(min_length=1,max_length=256)
    namespace:str=Field(min_length=1,max_length=1024)


class ConnectionCreate(Model):
    name:str=Field(min_length=1,max_length=200)
    target_alias:str=Field(min_length=1,max_length=128,pattern=r'^[A-Za-z][A-Za-z0-9_.-]*$')


class ConnectionUpdate(ConnectionCreate):
    base_revision:str=Field(min_length=1,max_length=128)


class LayerSave(Model):
    base_revision:str=Field(min_length=1,max_length=128)
    content:dict[str,JsonValue]
    dependencies:dict[str,str]


class JobSubmit(Model):
    operation:Literal['ingest','parse','extract','build_graph','ontology','validate_shacl','reason']
    request:dict[str,JsonValue]
    expected_workspace_revision:str=Field(min_length=1,max_length=128)
    idempotency_key:str=Field(min_length=1,max_length=128)


class Replay(Model):
    idempotency_key:str=Field(min_length=1,max_length=128)


class Membership(Model):
    user_id:str=Field(min_length=1,max_length=128)
    role:Literal['engineer','consultant','expert','admin','owner']
