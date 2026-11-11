"""Regressions from independently reproduced native boundary defects."""
import json
import pytest
from ontology_platform.semantic.dto import GraphBuildRequest, ReasoningRequest, SHACLRequest
from ontology_platform.semantic.errors import BackendError
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from test_semantic_boundary import artifact,common


def test_graph_never_accepts_plaintext_credentials_or_certification(tmp_path):
    backend=SemanticaBackend(tmp_path)
    forged={'entities':[{'id':'n1','type':'Node','text':'First','state':'CERTIFIED','metadata':{'password':'technical-test-secret'}}],'relationships':[]}
    source=artifact(tmp_path,'graph.json',json.dumps(forged))
    with pytest.raises(BackendError) as caught:
        backend.build_graph(GraphBuildRequest(**common(),source=source,graph_revision='g1'))
    assert 'technical-test-secret' not in json.dumps(caught.value.to_dict())


def test_normal_graph_candidates_are_draft_with_unknown_confidence(tmp_path):
    source=artifact(tmp_path,'graph.json',json.dumps({'entities':[{'id':'n1','type':'Node','text':'First'}],'relationships':[]}))
    result=SemanticaBackend(tmp_path).build_graph(GraphBuildRequest(**common(),source=source,graph_revision='g1'))
    assert result.data['entities'][0]['state']=='DRAFT'
    assert result.data['entities'][0]['confidence'] is None


def test_reason_confidence_unknown_is_null(tmp_path):
    facts=artifact(tmp_path,'facts.json',json.dumps(['Token(x)']))
    rules=artifact(tmp_path,'rules.json',json.dumps([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Mark(?x)'}]))
    result=SemanticaBackend(tmp_path).reason(ReasoningRequest(**common(),source=facts,rules=rules,graph_revision='g1',ruleset_revision='rules:v1'))
    assert result.data['inferred'][0]['confidence'] is None


@pytest.mark.parametrize('fact,condition,conclusion',[('Token(x)','Token(?1)','Mark(?1)'),('Token(a,b)','Token(?x)','Mark(?x)')])
def test_invalid_rule_grammar_and_arity_rejected(tmp_path,fact,condition,conclusion):
    facts=artifact(tmp_path,'facts.json',json.dumps([fact]))
    rules=artifact(tmp_path,'rules.json',json.dumps([{'id':'r1','conditions':[condition],'conclusion':conclusion}]))
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).reason(ReasoningRequest(**common(),source=facts,rules=rules,graph_revision='g1',ruleset_revision='rules:v1'))
    assert caught.value.code=='INVALID_INPUT'


@pytest.mark.parametrize('severity',['Warning','Info'])
def test_shacl_non_error_findings_preserved(tmp_path,severity):
    data=artifact(tmp_path,'data.ttl','<urn:n> <urn:p> "v" .')
    shape=f'@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:S> a sh:NodeShape ; sh:targetNode <urn:n> ; sh:property [ sh:path <urn:p> ; sh:minCount 2 ; sh:severity sh:{severity} ; sh:message "Missing second p" ] .'
    shapes=artifact(tmp_path,'shapes.ttl',shape)
    result=SemanticaBackend(tmp_path).validate_shacl(SHACLRequest(**common(),source=data,shapes=shapes,graph_revision='g1',shapes_revision='s1',suite_revision='q1'))
    assert not result.data['conforms']
    assert result.data['findings'] and result.data['findings'][0]['severity'].lower()==severity.lower()


def test_imported_shapes_are_explicitly_unsupported(tmp_path):
    data=artifact(tmp_path,'data.ttl','<urn:n> <urn:p> "v" .')
    shapes=artifact(tmp_path,'shapes.ttl','<urn:S> <http://www.w3.org/2002/07/owl#imports> <https://example.invalid/shapes> .')
    with pytest.raises(BackendError) as caught:
        SemanticaBackend(tmp_path).validate_shacl(SHACLRequest(**common(),source=data,shapes=shapes,graph_revision='g1',shapes_revision='s1',suite_revision='q1'))
    assert caught.value.code=='UNSUPPORTED_CAPABILITY'
