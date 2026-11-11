"""Same boundary contracts, distinctly marked real and Fake evidence."""
import importlib,json,os,subprocess,sys
from pathlib import Path
import pytest
from ontology_platform.semantic.errors import BackendError
from ontology_platform.semantic.backend import SemanticBackend
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from semantic_cases import OPERATIONS,RESULTS,request


def fake_class():
    return importlib.import_module('tests.fakes.semantic_backend').FakeBackend


@pytest.mark.parametrize('kind',['real','fake'])
@pytest.mark.parametrize('operation',OPERATIONS)
@pytest.mark.parametrize('case',['success','hash_mismatch','escape','missing_source_refs'])
def test_shared_contract(tmp_path,kind,operation,case):
    backend=SemanticaBackend(tmp_path) if kind=='real' else fake_class()(tmp_path)
    req=request(tmp_path,operation)
    if case=='hash_mismatch': req=req.model_copy(update={'source':req.source.model_copy(update={'sha256':'0'*64})})
    if case=='escape': req=req.model_copy(update={'source':req.source.model_copy(update={'path':'../outside'})})
    if case=='missing_source_refs': req=req.model_copy(update={'source_refs':()})
    if case!='success':
        with pytest.raises(BackendError) as caught: getattr(backend,operation)(req)
        assert caught.value.code=='INVALID_INPUT'
        assert caught.value.run_id==req.run_id and caught.value.__context__ is None
        return
    result=getattr(backend,operation)(req)
    assert isinstance(backend,SemanticBackend) and isinstance(result,RESULTS[operation])
    payload=json.loads(result.model_dump_json())
    assert payload['run_id']==req.run_id and payload['workspace_revision']=='w1'
    assert payload['source_refs']==['source:s1'] and result.artifact_refs
    assert bool('fake' in result.backend_version)==(kind=='fake')
    for item in result.artifact_refs:
        assert item.size==(tmp_path/item.path).stat().st_size
    if operation in ('extract','build_graph'):
        assert result.data['entities']
        for entity in result.data['entities']:
            assert entity['state']=='DRAFT' and entity['confidence'] is None
    if operation=='validate_shacl':
        assert result.data['conforms'] is False and result.data['findings']
    if operation=='reason':
        assert result.data['inferred'][0]['rule_version']=='rules:v1:r1'
        assert result.data['inferred'][0]['premise_refs']


def test_factory_rejects_fake(tmp_path):
    factory=importlib.import_module('ontology_platform.infrastructure.backend_factory')
    for kind in ('fake','unknown',''):
        with pytest.raises(ValueError): factory.create_backend(kind,tmp_path)
    assert isinstance(factory.create_backend('semantica',tmp_path),SemanticBackend)


def test_fake_failure_injection_is_sanitized(tmp_path):
    backend=fake_class()(tmp_path,fail_operation='reason')
    with pytest.raises(BackendError) as caught: backend.reason(request(tmp_path,'reason'))
    assert caught.value.code=='BACKEND_FAILURE' and caught.value.__context__ is None


@pytest.mark.parametrize('kind',['real','fake'])
def test_shared_invalid_semantic_rule_failure(tmp_path,kind):
    from semantic_cases import artifact
    req=request(tmp_path,'reason')
    req=req.model_copy(update={'rules':artifact(tmp_path,'rules.json',json.dumps([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Token(?x)'}]))})
    backend=SemanticaBackend(tmp_path) if kind=='real' else fake_class()(tmp_path,fail_operation='reason',fail_code='INVALID_INPUT')
    with pytest.raises(BackendError) as caught: backend.reason(req)
    assert caught.value.code=='INVALID_INPUT'
    assert caught.value.run_id==req.run_id and caught.value.__context__ is None
    assert not (tmp_path/'runs').exists()


def test_fake_requires_no_sdk_or_network(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code='''import sys,importlib.abc,socket\nclass Block(importlib.abc.MetaPathFinder):\n def find_spec(self,fullname,path=None,target=None):\n  if fullname.startswith("semantica"): raise AssertionError("Fake imported SDK")\nsys.meta_path.insert(0,Block())\ndef block(*a,**k): raise AssertionError("Fake used network")\nsocket.socket.connect=block\nfrom tests.fakes.semantic_backend import FakeBackend\nfrom tests.contract.semantic_cases import request\nfrom pathlib import Path\nr=FakeBackend(Path(sys.argv[1])).ingest(request(Path(sys.argv[1]),"ingest"))\nassert "fake" in r.backend_version\nassert not any(x.startswith("semantica") for x in sys.modules)\n'''
    env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+str(root/'src'))
    result=subprocess.run([sys.executable,'-P','-c',code,str(tmp_path)],env=env,cwd=root,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
