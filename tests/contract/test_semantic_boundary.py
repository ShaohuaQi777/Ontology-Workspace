"""Enterprise value/error/artifact boundary plus real native operation smoke."""
import ast
import hashlib
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from rdflib import URIRef
from ontology_platform.semantic.dto import ArtifactRef, IngestRequest, ParseRequest, ExtractRequest, GraphBuildRequest, OntologyRequest, SHACLRequest, ReasoningRequest
from ontology_platform.semantic.backend import SemanticBackend
from ontology_platform.semantic.errors import BackendError, invoke_guarded
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from ontology_platform.infrastructure.semantica_adapter.translation import to_platform_value


def artifact(root,name,content,kind='source'):
    data = content.encode() if isinstance(content,str) else content
    (root/name).write_bytes(data)
    return ArtifactRef(path=name,sha256=hashlib.sha256(data).hexdigest(),size=len(data),kind=kind,revision='v1')


def common(run='r1'):
    return dict(run_id=run,workspace_revision='w1',source_refs=('source:s1',),scope_ref='scope:technical')


def test_native_objects_do_not_escape():
    with pytest.raises(BackendError):
        to_platform_value({'nested':[URIRef('urn:native')]},run_id='r1')
    assert to_platform_value({'values':[None,True,7,'plain']},run_id='r1') == {'values':[None,True,7,'plain']}


def test_native_exceptions_are_wrapped_without_secret():
    def native():
        raise RuntimeError('technical-test-secret')
    with pytest.raises(BackendError) as caught:
        invoke_guarded(native,run_id='r1')
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert 'technical-test-secret' not in json.dumps(caught.value.to_dict())


def test_business_modules_do_not_import_semantica():
    for path in Path('src/ontology_platform').rglob('*.py'):
        if 'semantica_adapter' in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):
                assert not any(item.name.startswith('semantica') for item in node.names), path
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith('semantica'), path


def test_request_result_are_json_serializable(tmp_path):
    source = artifact(tmp_path,'source.csv','id,value\nn1,7\n')
    request = IngestRequest(**common(),source=source,source_revision='v1',format='csv')
    request.model_dump_json()
    backend = SemanticaBackend(tmp_path)
    assert isinstance(backend,SemanticBackend)
    result = backend.ingest(request)
    result.model_dump_json()
    assert result.backend_version == '0.7.0+ontologyworkspace.4'
    assert result.run_id == request.run_id and result.source_refs == request.source_refs
    assert result.artifact_refs and result.adapter_version


@pytest.mark.parametrize('path', ['/private/data','../private','a/../../private','C:\\private'])
def test_path_escape_precedes_native_execution(tmp_path,path):
    source = ArtifactRef(path=path,sha256='0'*64,size=1,kind='source',revision='v1')
    request = IngestRequest(**common(),source=source,source_revision='v1',format='csv')
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).ingest(request)
    assert caught.value.code == 'INVALID_INPUT'


def test_bad_hash_rejected_before_native(tmp_path):
    source = artifact(tmp_path,'source.csv','id\nn1\n').model_copy(update={'sha256':'0'*64})
    with pytest.raises(BackendError):
        SemanticaBackend(tmp_path).ingest(IngestRequest(**common(),source=source,source_revision='v1',format='csv'))


def test_secret_parameters_rejected(tmp_path):
    source = artifact(tmp_path,'source.csv','id\nn1\n')
    with pytest.raises(ValidationError):
        IngestRequest(**common(),source=source,source_revision='v1',format='csv',parameters={'password':'technical-test-secret'})


def test_real_seven_operations(tmp_path):
    backend = SemanticaBackend(tmp_path)
    csv = artifact(tmp_path,'source.csv','id,value\nn1,7\n')
    assert backend.ingest(IngestRequest(**common('ingest'),source=csv,source_revision='v1',format='csv')).data['file_type'] == 'csv'
    parsed = backend.parse(ParseRequest(**common('parse'),source=csv,source_revision='v1',format='csv'))
    assert parsed.data['rows'] == [{'id':'n1','value':'7'}]
    text = artifact(tmp_path,'text.txt','Apple acquired Microsoft in California.')
    extracted = backend.extract(ExtractRequest(**common('extract'),source=text,source_revision='v1'))
    assert extracted.data['entities']
    assert all(item['state'] == 'DRAFT' for item in extracted.data['entities'])
    assert all(item['confidence'] is None for item in extracted.data['entities'])
    graph = artifact(tmp_path,'graph.json',json.dumps({'entities':[{'id':'n1','type':'Node','text':'First'},{'id':'n2','type':'Node','text':'Second'}], 'relationships':[{'source':'n1','target':'n2','type':'linksTo'}]}))
    built = backend.build_graph(GraphBuildRequest(**common('graph'),source=graph,graph_revision='g1'))
    assert len(built.data['entities']) == 2
    ttl = artifact(tmp_path,'ontology.ttl','@prefix owl: <http://www.w3.org/2002/07/owl#> . <urn:Node> a owl:Class .')
    imported = backend.ontology(OntologyRequest(**common('ontology'),source=ttl,schema_revision='t1',action='import'))
    assert imported.data['format'] == 'nt'
    data = artifact(tmp_path,'data.ttl','<urn:n> <urn:p> "v" .')
    shapes = artifact(tmp_path,'shapes.ttl','@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:S> a sh:NodeShape ; sh:targetNode <urn:n> ; sh:property [ sh:path <urn:p> ; sh:minCount 1 ] .')
    validated = backend.validate_shacl(SHACLRequest(**common('shacl'),source=data,shapes=shapes,graph_revision='g1',suite_revision='q1',shapes_revision='s1'))
    assert validated.data['conforms']
    facts = artifact(tmp_path,'facts.json',json.dumps(['Token(x)']))
    rules = artifact(tmp_path,'rules.json',json.dumps([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Mark(?x)'}]))
    inferred = backend.reason(ReasoningRequest(**common('reason'),source=facts,rules=rules,graph_revision='g1',ruleset_revision='rules:v1'))
    assert inferred.data['inferred'][0]['conclusion'] == 'Mark(x)'
    assert inferred.data['inferred'][0]['rule_version'] == 'rules:v1:r1'
    assert inferred.data['inferred'][0]['premise_refs']


def test_staging_symlink_does_not_write_outside_root(tmp_path):
    root=tmp_path/'root'; root.mkdir()
    outside=tmp_path/'outside'; outside.mkdir()
    (root/'runs').symlink_to(outside,target_is_directory=True)
    source=artifact(root,'source.csv','id\nn1\n')
    with pytest.raises(BackendError):
        SemanticaBackend(root).ingest(IngestRequest(**common(),source=source,source_revision='v1',format='csv'))
    assert list(outside.iterdir()) == []


def test_actual_native_error_does_not_expose_source_or_logs(tmp_path,capfd):
    source=artifact(tmp_path,'invalid.json','{technical-test-secret')
    request=ParseRequest(**common(),source=source,source_revision='v1',format='json')
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).parse(request)
    assert caught.value.__context__ is None
    assert 'technical-test-secret' not in json.dumps(caught.value.to_dict())
    captured=capfd.readouterr()
    assert not captured.out and not captured.err


def test_recursive_and_unbound_rules_fail_closed(tmp_path):
    facts=artifact(tmp_path,'facts.json',json.dumps(['Token(x)']))
    for index,rule in enumerate([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Token(?x)'},
                                 {'id':'r1','conditions':['Token(?x)'],'conclusion':'Mark(?y)'}]):
        rules=artifact(tmp_path,'rules.json',json.dumps([rule]))
        with pytest.raises(BackendError) as caught:
            SemanticaBackend(tmp_path).reason(ReasoningRequest(**common('invalid'+str(index)),source=facts,rules=rules,graph_revision='g1',ruleset_revision='rules:v1'))
        assert caught.value.code == 'INVALID_INPUT'


def test_platform_is_installed_not_only_cwd_pythonpath():
    from importlib.metadata import version
    assert version('ontology-workspace') == '0.1.0'


def test_shacl_advanced_sparql_fails_closed_before_native_validation(tmp_path):
    data=artifact(tmp_path,'data.ttl','<urn:n> <urn:p> "v" .')
    shapes=artifact(tmp_path,'advanced.ttl','@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:S> a sh:NodeShape ; sh:targetNode <urn:n> ; sh:sparql [ sh:select "SELECT $this WHERE { FILTER(false) }" ] .')
    request=SHACLRequest(**common(),source=data,shapes=shapes,graph_revision='g1',suite_revision='q1',shapes_revision='s1')
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).validate_shacl(request)
    assert caught.value.code == 'UNSUPPORTED_CAPABILITY'


def test_child_timeout_has_platform_timeout_code(tmp_path,monkeypatch):
    import subprocess
    def timeout(*args,**kwargs):
        raise subprocess.TimeoutExpired('native child',1)
    monkeypatch.setattr(subprocess,'run',timeout)
    source=artifact(tmp_path,'source.csv','id\nn1\n')
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).ingest(IngestRequest(**common(),source=source,source_revision='v1',format='csv'))
    assert caught.value.code == 'TIMEOUT' and caught.value.retryable
    assert caught.value.__context__ is None
