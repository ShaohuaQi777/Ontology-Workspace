"""POSIX directory-capability I/O: no symlink traversal or path check/use gap.

The caller authorizes the root inode; same-UID malicious processes are not an OS
security boundary. Retain descriptors throughout child execution and publication.
"""
import os
from pathlib import PurePosixPath
import stat

MAX_BYTES=1048576


def components(path):
    if type(path) is not str or PurePosixPath(path).is_absolute() or '\\' in path or ':' in path or '\x00' in path:
        raise ValueError('Invalid artifact path')
    parts=path.split('/')
    if any(part in ('','..','.') for part in parts):
        raise ValueError('Invalid artifact path')
    return parts


class Directory:
    def __init__(self,fd): self.fd=fd
    def __enter__(self): return self
    def __exit__(self,*args): os.close(self.fd)

    @classmethod
    def root(cls,path):
        if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'):
            raise ValueError('Descriptor backend unavailable on this platform')
        return cls(os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))

    def directory(self,name,*,create=False):
        if len(components(name))!=1: raise ValueError('Invalid directory name')
        if create:
            try: os.mkdir(name,mode=0o700,dir_fd=self.fd)
            except FileExistsError: pass
        return Directory(os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.fd))

    def read(self,path,*,expected_size=None):
        parts=components(path); fd=os.dup(self.fd)
        try:
            for part in parts[:-1]:
                next_fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                os.close(fd); fd=next_fd
            file_fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            with os.fdopen(file_fd,'rb') as stream:
                info=os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_BYTES or (expected_size is not None and info.st_size!=expected_size):
                    raise ValueError('Invalid artifact size/type')
                data=stream.read(MAX_BYTES+1)
                if len(data)>MAX_BYTES or (expected_size is not None and len(data)!=expected_size):
                    raise ValueError('Invalid artifact bytes')
                return data
        finally: os.close(fd)

    def write(self,name,data):
        if len(components(name))!=1 or type(data) is not bytes or len(data)>MAX_BYTES:
            raise ValueError('Invalid bounded artifact output')
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        with os.fdopen(fd,'wb') as stream: stream.write(data)
