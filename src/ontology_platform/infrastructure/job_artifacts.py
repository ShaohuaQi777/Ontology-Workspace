"""Bounded per-job native input/output roots inside the authorized private tree."""
import hashlib,uuid
from .source_policy import FORMATS
from ontology_platform.infrastructure.semantica_adapter.secure_io import Directory
from ontology_platform.domain.service_errors import ServiceError


class JobArtifacts:
    def __init__(self,root): self.root=root

    @staticmethod
    def _id(value):
        if str(uuid.UUID(value))!=value: raise ValueError('Invalid job identifier')

    def prepare(self,project_id,job_id,bindings,inputs):
        self._id(project_id); self._id(job_id)
        paths={}
        with Directory.root(self.root) as root,root.directory(project_id) as project,project.directory('jobs',create=True) as jobs,jobs.directory(job_id,create=True) as job:
            for key,data in inputs.items():
                if key not in ('source','shapes','rules'): raise ValueError('Invalid native input')
                name=key+'.'+FORMATS[bindings[key]['format']]
                job.write(name,data); paths[key]=name
        return self.root/project_id/'jobs'/job_id,paths

    def read(self,project_id,job_id,path,size,sha256):
        try:
            self._id(project_id); self._id(job_id)
            with Directory.root(self.root) as root,root.directory(project_id) as project,project.directory('jobs') as jobs,jobs.directory(job_id) as job:
                data=job.read(path,expected_size=size)
            if hashlib.sha256(data).hexdigest()!=sha256: raise ValueError('Job artifact hash mismatch')
            return data
        except Exception: raise ServiceError('INVALID_JOB') from None
