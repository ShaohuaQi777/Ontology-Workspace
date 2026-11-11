"""Durable pure-step Worker around the real bounded native SDK factory."""
import json,threading
from ontology_platform.domain.service_errors import ServiceError
from ontology_platform.semantic.errors import BackendError
from ontology_platform.infrastructure.backend_factory import create_backend
from ontology_platform.infrastructure.job_artifacts import JobArtifacts
from .jobs import REQUESTS


class NativeJobWorker:
    def __init__(self,jobs): self.jobs=jobs

    def run_one(self,worker_id):
        job=self.jobs.claim(worker_id)
        if job is None: return False
        stop=threading.Event()
        def heartbeat():
            while not stop.wait(20):
                if not self.jobs.heartbeat(job.job_id,worker_id): return
        timer=threading.Thread(target=heartbeat,daemon=True); timer.start()
        try:
            row,inputs=self.jobs.prepare(job.job_id,worker_id)
            if row['cancel_requested']:
                self.jobs.finish(job.job_id,worker_id); return True
            bindings=json.loads(row['bindings_json'])
            root,paths=JobArtifacts(self.jobs.workspaces.sources.root).prepare(job.project_id,job.job_id,bindings,inputs)
            payload=json.loads(row['request_json'])
            for key,path in paths.items(): payload[key]['path']=path
            request=REQUESTS[job.operation].model_validate_json(json.dumps(payload,allow_nan=False))
            backend=create_backend('semantica',root)
            result=getattr(backend,job.operation)(request)
            self.jobs.finish(job.job_id,worker_id,result=result)
        except (ServiceError,BackendError) as failure: self.jobs.finish(job.job_id,worker_id,error_code=failure.code)
        except Exception: self.jobs.finish(job.job_id,worker_id,error_code='BACKEND_FAILURE')
        finally:
            stop.set(); timer.join(timeout=2)
        return True
