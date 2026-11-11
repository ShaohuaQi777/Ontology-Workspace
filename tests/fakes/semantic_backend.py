"""Test-only fixed protocol responses; never a semantic inference implementation.

No SDK imports/network. Only the approved domain-neutral shared fixture outcomes
are replayed; passing Fake tests does not prove real semantic capability.
"""
import hashlib,json
from pathlib import Path
from uuid import uuid4
from ontology_platform.semantic import dto
from ontology_platform.semantic.errors import BackendError,invoke_guarded
from ontology_platform.infrastructure.semantica_adapter.secure_io import Directory

REQUESTS={'ingest':dto.IngestRequest,'parse':dto.ParseRequest,'extract':dto.ExtractRequest,'build_graph':dto.GraphBuildRequest,'ontology':dto.OntologyRequest,'validate_shacl':dto.SHACLRequest,'reason':dto.ReasoningRequest}
RESULTS={'ingest':dto.IngestResult,'parse':dto.ParseResult,'extract':dto.ExtractionResult,'build_graph':dto.GraphResult,'ontology':dto.OntologyResult,'validate_shacl':dto.ValidationResult,'reason':dto.ReasoningResult}


class FakeBackend:
    backend_version='fake-contract-0.1.0'
    def __init__(self,artifact_root:Path,*,fail_operation:str|None=None,fail_code:str='BACKEND_FAILURE'):
        self.artifact_root=Path(artifact_root)
        self.fail_operation=fail_operation
        self.fail_code=fail_code

    def _execute(self,operation,request):
        request=REQUESTS[operation].model_validate_json(request.model_dump_json())
        with Directory.root(self.artifact_root) as root:
            for key in ('source','shapes','rules'):
                if hasattr(request,key):
                    ref=getattr(request,key)
                    source=root.read(ref.path,expected_size=ref.size)
                    if hashlib.sha256(source).hexdigest()!=ref.sha256: raise ValueError('Invalid source digest')
            if operation==self.fail_operation:
                raise BackendError(self.fail_code,'Test backend configured failure',request.run_id,False)
            entity={'id':'fake-technical-node','state':'DRAFT','confidence':None}
            data={'ingest':{'file_type':'csv','size':request.source.size},
                  'parse':{'headers':['id','value'],'rows':[{'id':'n1','value':'7'}],'row_count':1},
                  'extract':{'entities':[entity],'relationships':[],'events':[]},
                  'build_graph':{'entities':[entity],'relationships':[]},
                  'ontology':{'format':'nt','state':'DRAFT'},
                  'validate_shacl':{'conforms':False,'findings':[{'severity':'Violation','message':'Fixed technical test violation','source_refs':list(request.source_refs)}]},
                  'reason':{'asserted':['Token(x)'],'inferred':[{'conclusion':'Mark(x)','confidence':None,'rule_version':getattr(request,'ruleset_revision','rules:v1')+':r1','premise_refs':['sha256:'+request.source.sha256]}]}}[operation]
            content=json.dumps(data,sort_keys=True,allow_nan=False).encode()
            name='fake-result-'+uuid4().hex+'.json'; root.write(name,content)
            artifact=dto.ArtifactRef(path=name,sha256=hashlib.sha256(content).hexdigest(),size=len(content),kind='fake-result',revision=request.workspace_revision)
            return RESULTS[operation](run_id=request.run_id,workspace_revision=request.workspace_revision,backend_version=self.backend_version,adapter_version='fake-0.1.0',source_refs=request.source_refs,artifact_refs=(artifact,),data=data)

    def _call(self,operation,request):
        return invoke_guarded(lambda:self._execute(operation,request),run_id=request.run_id)

    def ingest(self,request:dto.IngestRequest)->dto.IngestResult: return self._call('ingest',request)
    def parse(self,request:dto.ParseRequest)->dto.ParseResult: return self._call('parse',request)
    def extract(self,request:dto.ExtractRequest)->dto.ExtractionResult: return self._call('extract',request)
    def build_graph(self,request:dto.GraphBuildRequest)->dto.GraphResult: return self._call('build_graph',request)
    def ontology(self,request:dto.OntologyRequest)->dto.OntologyResult: return self._call('ontology',request)
    def validate_shacl(self,request:dto.SHACLRequest)->dto.ValidationResult: return self._call('validate_shacl',request)
    def reason(self,request:dto.ReasoningRequest)->dto.ReasoningResult: return self._call('reason',request)
    def capabilities(self)->list[dto.Capability]:
        return [dto.Capability(operation=operation,supported=True,backend_version=self.backend_version,limitations=('Test-only fixed contract replay, not semantic capability',)) for operation in REQUESTS]
