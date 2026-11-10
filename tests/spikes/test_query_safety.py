"""AST preflight is safety logic, never a substitute query engine."""
import pytest
from spikes.semantica.query_safety import validate_readonly_sparql


@pytest.mark.parametrize('query', [
    'SELECT ?o WHERE { <urn:s> <urn:p> ?o }',
    'ASK WHERE { <urn:s> <urn:p> <urn:o> }',
    'SELECT ?s WHERE { ?s <urn:p> "SERVICE INSERT DELETE" }',
])
def test_readonly_queries_are_allowed(query):
    assert validate_readonly_sparql(query) == query


@pytest.mark.parametrize('query', [
    'INSERT DATA { <urn:s> <urn:p> <urn:o> }',
    'DELETE WHERE { ?s ?p ?o }',
    'CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }',
    'SELECT ?s WHERE { SERVICE <https://example.invalid/> { ?s ?p ?o } }',
    'SELECT ?s FROM <https://example.invalid/data> WHERE { ?s ?p ?o }',
    'ASK FROM NAMED <https://example.invalid/data> WHERE { ?s ?p ?o }',
    'SELECT (<https://example.invalid/function>(?s) AS ?x) WHERE { ?s ?p ?o }',
    'SELECT ?s WHERE { ?s ?p ?o }; DELETE WHERE { ?s ?p ?o }',
])
def test_mutation_and_network_are_rejected(query):
    with pytest.raises(ValueError):
        validate_readonly_sparql(query)


def test_invalid_query_does_not_return_parser_exception():
    try:
        validate_readonly_sparql('synthetic-parser-private-value')
    except ValueError as error:
        assert 'synthetic-parser-private-value' not in str(error)
        assert error.__context__ is None
    else:
        pytest.fail('Malformed query must fail')
