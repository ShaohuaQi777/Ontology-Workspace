"""Readonly/no-network syntax guard. Query semantics remain native Semantica."""
from collections.abc import Mapping
from pyparsing import ParseResults
from rdflib.plugins.sparql.parser import parseQuery


def validate_readonly_sparql(query: str) -> str:
    if type(query) is not str or not query.strip() or len(query) > 16000:
        raise ValueError('Invalid SPARQL input')
    parsed = None
    try:
        parsed = parseQuery(query)
    except Exception:
        pass
    # Raise outside parser exception handler: no original query/parser context retained.
    if parsed is None:
        raise ValueError('Invalid SPARQL syntax')
    if getattr(parsed[1], 'name', None) not in {'SelectQuery', 'AskQuery'}:
        raise ValueError('Only SELECT and ASK are supported')
    pending = [parsed]
    count = 0
    while pending:
        node = pending.pop()
        count += 1
        if count > 4000:
            raise ValueError('SPARQL structure exceeds limits')
        if getattr(node, 'name', None) in {'ServiceGraphPattern', 'DatasetClause', 'Function'}:
            raise ValueError('External service, dataset or custom function is forbidden')
        if isinstance(node, ParseResults):
            # ParseResults is also Mapping, but values() omits positional AST children.
            pending.extend(node)
            pending.extend(node.values())
        elif isinstance(node, Mapping):
            pending.extend(node.values())
        elif isinstance(node, (list, tuple)):
            pending.extend(node)
    return query
