"""Operator-only immutable target aliases; no native SDK or public locators."""
from dataclasses import dataclass,field
from types import MappingProxyType
from pathlib import Path
import hashlib,ipaddress,json,os,re,stat
from urllib.parse import urlsplit
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.semantic.dto import reject_credential_authority

ALIAS=re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,127}$')


@dataclass(frozen=True)
class Target:
    alias:str
    kind:str
    locator:str=field(repr=False)
    credential_ref:str|None=field(default=None,repr=False)

    @property
    def binding_hash(self):
        return hashlib.sha256(json.dumps([self.alias,self.kind,self.locator,self.credential_ref],separators=(',',':')).encode()).hexdigest()


def validate_target(target):
    if type(target) is not Target or not ALIAS.fullmatch(target.alias) or target.kind not in {'sqlite','http','feishu'} or type(target.locator) is not str:
        raise ValueError('Invalid trusted target')
    if target.credential_ref is not None and (type(target.credential_ref) is not str or not re.fullmatch(r'env:ONTOLOGY_SECRET_[A-Z0-9_]{1,100}',target.credential_ref)):
        raise ValueError('Invalid credential reference')
    if target.kind=='sqlite':
        path=Path(target.locator)
        if not path.is_absolute() or any(part.is_symlink() for part in (path,*path.parents)):
            raise ValueError('Invalid private target')
        try:
            info=path.stat(); parent=path.parent.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077 or parent.st_uid!=os.geteuid() or parent.st_mode&0o077:
                raise ValueError('Invalid private target')
        except OSError: raise ValueError('Invalid private target') from None
    else:
        reject_credential_authority(target.locator)
        try:
            parsed=urlsplit(target.locator); port=parsed.port
            if parsed.scheme!='https' or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment or any(ch.isspace() for ch in target.locator):
                raise ValueError('Invalid HTTPS target')
            host=parsed.hostname.casefold().rstrip('.')
            if host=='localhost' or host.endswith(('.localhost','.local','.internal')):
                raise ValueError('Invalid HTTPS target')
            try: address=ipaddress.ip_address(host)
            except ValueError: address=None
            if address is not None and not address.is_global: raise ValueError('Invalid HTTPS target')
            if target.kind=='feishu' and (host!='open.feishu.cn' or port not in (None,443) or parsed.path not in ('','/')):
                raise ValueError('Invalid Feishu target')
        except ValueError: raise ValueError('Invalid HTTPS target') from None


class TargetRegistry:
    def __init__(self,targets,project_grants):
        checked=dict(targets)
        for alias,target in checked.items():
            validate_target(target)
            if alias!=target.alias: raise ValueError('Invalid trusted alias')
        grants={alias:frozenset(projects) for alias,projects in project_grants.items()}
        if not set(grants)<=set(checked): raise ValueError('Invalid target grants')
        self._targets=MappingProxyType(checked); self._grants=MappingProxyType(grants)

    def resolve(self,alias,project_id):
        if alias not in self._targets: raise ServiceError('INVALID_CONNECTION')
        if project_id not in self._grants.get(alias,()): raise ServiceError('FORBIDDEN')
        return self._targets[alias]


@dataclass(frozen=True)
class ConnectionView:
    connection_id:str
    project_id:str
    name:str
    target_alias:str
    kind:str
    revision:str
    status:str='CONFIGURED'
