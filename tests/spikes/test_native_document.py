"""Direct native extension tests; no module injection or patched metadata."""
import json
import socket
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDFS
from semantica.ontology.document import OntologyDocument
from spikes.semantica.fixtures import COMPLEX_TTL


def test_complex_roundtrip_isomorphic():
    document = OntologyDocument.from_rdf(COMPLEX_TTL, format='turtle')
    exported = document.serialize(format='turtle')
    assert isomorphic(Graph().parse(data=COMPLEX_TTL, format='turtle'), Graph().parse(data=exported, format='turtle'))


def test_label_edit_is_immutable_and_scoped():
    source = COMPLEX_TTL + '<https://example.invalid/probe/Node> <http://www.w3.org/2000/01/rdf-schema#label> "节点"@zh .'
    original = OntologyDocument.from_rdf(source)
    edited = original.with_label('https://example.invalid/probe/Node', 'Changed technical label')
    before = Graph().parse(data=source, format='turtle')
    after = Graph().parse(data=edited.serialize(), format='turtle')
    assert isomorphic(before, Graph().parse(data=original.serialize(), format='turtle'))
    subject = URIRef('https://example.invalid/probe/Node')
    expected = Graph()
    for triple in before:
        expected.add(triple)
    expected.remove((subject, RDFS.label, Literal('Technical node')))
    expected.add((subject, RDFS.label, Literal('Changed technical label')))
    assert isomorphic(expected, after)
    assert (subject, RDFS.label, Literal('节点', lang='zh')) in after


@pytest.mark.parametrize('data,format', [
    (json.dumps({'@context': 'https://example.invalid/context', '@id': 'urn:s'}), 'json-ld'),
    (json.dumps({'@context': {'@import': 'https://example.invalid/context'}, '@id': 'urn:s'}), 'json-ld'),
    ('<!DOCTYPE rdf:RDF [<!ENTITY private SYSTEM "file:///not-authorized">]><rdf:RDF/>', 'xml'),
])
def test_remote_context_and_dtd_rejected_without_network(monkeypatch, data, format):
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Outbound connection is forbidden')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    with pytest.raises(ValueError):
        OntologyDocument.from_rdf(data, format=format)
    assert attempts == []


def test_jsonld_is_explicitly_deferred_until_full_preservation():
    source = json.dumps({'@context': {'ex': 'https://example.invalid/'}, '@id': 'ex:n1', 'ex:p': 'value'})
    with pytest.raises(ValueError, match='Unsupported RDF format'):
        OntologyDocument.from_rdf(source, format='json-ld')


@pytest.mark.parametrize('uri', ['javascript:private', '../private', 'https://example.invalid/missing', 'bad uri'])
def test_invalid_or_missing_class_rejected_without_mutation(uri):
    document = OntologyDocument.from_rdf(COMPLEX_TTL)
    with pytest.raises(ValueError):
        document.with_label(uri, 'New label')
    assert isomorphic(Graph().parse(data=COMPLEX_TTL, format='turtle'), Graph().parse(data=document.serialize(), format='turtle'))


def test_oversized_document_rejected():
    with pytest.raises(ValueError):
        OntologyDocument.from_rdf(' ' * (1024 * 1024 + 1))
