"""Explicit provider references only; no plaintext config or environment scanning."""
import os,re
from typing import Protocol
from pydantic import SecretStr
from ontology_platform.domain.service_errors import ServiceError


class SecretProvider(Protocol):
    def resolve(self,reference:str)->SecretStr: ...


class EnvironmentSecretProvider:
    def __init__(self,allowed_refs:set[str],environ=None):
        self._allowed=frozenset(allowed_refs)
        self._environ=os.environ if environ is None else environ

    def resolve(self,reference:str)->SecretStr:
        if (not isinstance(reference,str) or reference not in self._allowed
                or not re.fullmatch(r'env:ONTOLOGY_SECRET_[A-Z0-9_]{1,100}',reference)):
            raise ServiceError('SECRET_UNAVAILABLE')
        value=self._environ.get(reference[4:])
        if not isinstance(value,str) or not value or len(value.encode())>8192:
            raise ServiceError('SECRET_UNAVAILABLE')
        return SecretStr(value)
