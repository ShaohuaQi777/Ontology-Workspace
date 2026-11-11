"""Descriptor-capability per-project source files; paths never come from uploads."""
from pathlib import Path
import hashlib,stat,uuid
from ontology_platform.infrastructure.semantica_adapter.secure_io import Directory
from .source_policy import FORMATS


class SourceStore:
    def __init__(self,root,database_path):
        path=Path(root).absolute()
        if any(part.is_symlink() for part in (*path.parents,path)):
            raise ValueError('Source root symlinks are not permitted')
        if not path.is_dir() or stat.S_IMODE(path.stat().st_mode)&0o077:
            raise ValueError('Private source root required')
        if Path(database_path).absolute().is_relative_to(path):
            raise ValueError('Source root must not contain metadata')
        self.root=path

    @staticmethod
    def _id(value):
        if type(value) is not str or str(uuid.UUID(value))!=value: raise ValueError('Invalid scoped identifier')
        return value

    def write(self,project_id,source_id,format,data):
        self._id(project_id); self._id(source_id)
        name=source_id+'.'+FORMATS[format]
        with Directory.root(self.root) as root,root.directory(project_id,create=True) as project,project.directory('sources',create=True) as sources:
            sources.write(name,data)
        return name

    def read(self,project_id,name,size,sha256):
        self._id(project_id)
        with Directory.root(self.root) as root,root.directory(project_id) as project,project.directory('sources') as sources:
            data=sources.read(name,expected_size=size)
        if hashlib.sha256(data).hexdigest()!=sha256: raise ValueError('Source hash mismatch')
        return data
