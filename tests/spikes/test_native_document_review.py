"""Regression cases grounded in independent E1 security review."""
import json
import socket
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDFS
from semantica.ontology.document import OntologyDocument


@pytest.mark.parametrize('context', [[['http://127.0.0.1:9/context']], [['file:///not-authorized']]])
def test_nested_context_rejected_before_io(monkeypatch, context):
    attempts = []
    def deny(*args):
        attempts.append(True)
        raise AssertionError('No connections allowed')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    with pytest.raises(ValueError):
        OntologyDocument.from_rdf(json.dumps({'@context': context, '@id': 'urn:s'}), format='json-ld')
    assert attempts == []


@pytest.mark.parametrize('source', [
    {'@id': 'urn:g', '@graph': [{'@id': 'urn:s', 'urn:p': {'@value': 'v'}}]},
    [{'@id': 'urn:default', 'urn:p': 'd'}, {'@id': 'urn:g', '@graph': [{'@id': 'urn:s', 'urn:p': 'v'}]}],
])
def test_named_graph_is_never_silently_discarded(source):
    with pytest.raises(ValueError):
        OntologyDocument.from_rdf(json.dumps(source), format='json-ld')


@pytest.mark.parametrize('format', ['turtle', 'nt'])
def test_typed_literal_lexical_form_preserved(format):
    source = '<urn:s> <urn:p> "01"^^<http://www.w3.org/2001/XMLSchema#integer> .'
    document = OntologyDocument.from_rdf(source, format=format)
    assert '"01"^^' in document.serialize(format='nt')
    roundtrip = OntologyDocument.from_rdf(document.serialize(), format='turtle')
    assert '"01"^^' in roundtrip.serialize(format='nt')


@pytest.mark.parametrize('value', ['+01', '01', '1.00', '1.00e+01'])
def test_turtle_numeric_shorthand_lexical_preserved(value):
    document = OntologyDocument.from_rdf(f'<urn:s> <urn:p> {value} .')
    assert f'"{value}"^^' in document.serialize(format='nt')


@pytest.mark.parametrize('format', ['turtle', 'nt'])
@pytest.mark.parametrize('datatype,lexical', [('token', '  alpha   beta  '), ('normalizedString', 'alpha\\tbeta\\nend')])
def test_string_datatype_whitespace_preserved_during_unrelated_edit(format, datatype, lexical):
    term = f'"{lexical}"^^<http://www.w3.org/2001/XMLSchema#{datatype}>'
    source = f'<urn:s> <urn:p> {term} .\n<urn:c> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class> .'
    document = OntologyDocument.from_rdf(source, format=format)
    # N-Triples permits a raw tab; RDFLib uses raw tab rather than \\t escaping.
    # This is the same RDF lexical term, unlike whitespace collapsed to spaces.
    expected_term = term.replace('\\t', '\t')
    assert expected_term in document.serialize(format='nt')
    assert expected_term in OntologyDocument.from_rdf(document.serialize()).serialize(format='nt')
    assert expected_term in document.with_label('urn:c', 'New').serialize(format='nt')


def test_language_match_is_case_insensitive():
    source = '<urn:c> a <http://www.w3.org/2002/07/owl#Class> ; <http://www.w3.org/2000/01/rdf-schema#label> "Old"@en, "旧"@zh .'
    edited = OntologyDocument.from_rdf(source).with_label('urn:c', 'New', language='EN')
    result = Graph().parse(data=edited.serialize(), format='turtle')
    labels = list(result.objects(URIRef('urn:c'), RDFS.label))
    assert len(labels) == 2
    assert any(str(label) == 'New' and label.language.lower() == 'en' for label in labels)
    assert any(str(label) == '旧' and label.language == 'zh' for label in labels)
    assert not any(str(label) == 'Old' for label in labels)
