"""Synchronous bounded POSIX subprocess SDK boundary, not a product Worker queue."""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from ...semantic import dto
from ...semantic.errors import BackendError, ERROR_MESSAGES, invoke_guarded
from .translation import to_platform_value
from .secure_io import Directory
from .input_policy import preflight

ADAPTER_VERSION = '0.1.0'
REQUESTS = {'ingest':dto.IngestRequest,'parse':dto.ParseRequest,'extract':dto.ExtractRequest,
            'build_graph':dto.GraphBuildRequest,'ontology':dto.OntologyRequest,
            'validate_shacl':dto.SHACLRequest,'reason':dto.ReasoningRequest}
RESULTS = {'ingest':dto.IngestResult,'parse':dto.ParseResult,'extract':dto.ExtractionResult,
           'build_graph':dto.GraphResult,'ontology':dto.OntologyResult,
           'validate_shacl':dto.ValidationResult,'reason':dto.ReasoningResult}


class SemanticaBackend:
    def __init__(self, artifact_root: Path, *, timeout_seconds: int = 90):
        self.artifact_root = Path(artifact_root).resolve(strict=True)
        if not self.artifact_root.is_dir() or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
            raise ValueError('Invalid backend configuration')
        self.timeout_seconds = timeout_seconds
        self.backend_version = version('semantica')
        if self.backend_version != '0.7.0+ontologyworkspace.4':
            raise ValueError('Unsupported installed semantic backend version')

    def _execute(self, operation, request):
        request = REQUESTS[operation].model_validate_json(request.model_dump_json())
        with Directory.root(self.artifact_root) as root:
            inputs={}
            for key in ('source','shapes','rules'):
                if hasattr(request,key):
                    ref=getattr(request,key)
                    data=root.read(ref.path,expected_size=ref.size)
                    if hashlib.sha256(data).hexdigest()!=ref.sha256:
                        raise ValueError('Invalid artifact hash')
                    inputs[key]=data
            # No source or request persistence occurs until all input policies pass.
            preflight(operation,request,inputs)
            identifier=uuid.uuid4().hex
            with root.directory('runs',create=True) as runs, runs.directory(request.run_id,create=True) as run, run.directory(identifier,create=True) as staging:
                paths={}
                for key,data in inputs.items():
                    paths[key]=key+Path(getattr(request,key).path).suffix
                    staging.write(paths[key],data)
                job={'operation':operation,'request':request.model_dump(mode='json'),'paths':paths}
                staging.write('request.json',json.dumps(job,allow_nan=False).encode())
                env={'PATH':os.defpath,'PYTHONPATH':str(Path(__file__).resolve().parents[3]),
                     'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
                     'TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
                     'HF_HOME':'./cache','XDG_CACHE_HOME':'./cache','HOME':'/nonexistent'}
                completed=subprocess.run([sys.executable,'-P','-m','ontology_platform.infrastructure.semantica_adapter.worker','--directory-fd',str(staging.fd)],
                                         env=env,cwd=self.artifact_root,pass_fds=(staging.fd,),stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=self.timeout_seconds)
                if completed.returncode:
                    raise RuntimeError('Native worker did not return a result')
                outcome=json.loads(staging.read('response.json'))
                if 'error' in outcome:
                    code=outcome['error']['code']
                    raise BackendError(code,ERROR_MESSAGES[code],request.run_id,code=='TIMEOUT')
                data=to_platform_value(outcome['data'],run_id=request.run_id)
                artifacts=[]
                prefix=f'runs/{request.run_id}/{identifier}/'
                for filename,kind in [('response.json','result'),*outcome.get('artifacts',[])]:
                    contents=staging.read(filename); digest=hashlib.sha256(contents).hexdigest()
                    artifacts.append(dto.ArtifactRef(path=prefix+filename,sha256=digest,size=len(contents),kind=kind,revision='sha256:'+digest))
                return RESULTS[operation](run_id=request.run_id,workspace_revision=request.workspace_revision,
                                          backend_version=self.backend_version,adapter_version=ADAPTER_VERSION,
                                          source_refs=request.source_refs,artifact_refs=tuple(artifacts),data=data)

    def _call(self, operation, request):
        return invoke_guarded(lambda:self._execute(operation,request),run_id=request.run_id)

    def ingest(self, request: dto.IngestRequest) -> dto.IngestResult: return self._call('ingest',request)
    def parse(self, request: dto.ParseRequest) -> dto.ParseResult: return self._call('parse',request)
    def extract(self, request: dto.ExtractRequest) -> dto.ExtractionResult: return self._call('extract',request)
    def build_graph(self, request: dto.GraphBuildRequest) -> dto.GraphResult: return self._call('build_graph',request)
    def ontology(self, request: dto.OntologyRequest) -> dto.OntologyResult: return self._call('ontology',request)
    def validate_shacl(self, request: dto.SHACLRequest) -> dto.ValidationResult: return self._call('validate_shacl',request)
    def reason(self, request: dto.ReasoningRequest) -> dto.ReasoningResult: return self._call('reason',request)

    def capabilities(self) -> list[dto.Capability]:
        return [dto.Capability(operation=operation,supported=True,backend_version=self.backend_version,
                               limitations=('POSIX bounded local artifacts; scope_ref is context, not completed RBAC',)) for operation in REQUESTS]
