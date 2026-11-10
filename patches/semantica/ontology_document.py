"""Semantica native immutable RDF document extension.

SPDX-License-Identifier: MIT
Platform governance and authorization remain outside this semantic SDK module.
No imports/context/URI fetching, arbitrary path input, or reasoning is performed.
"""
from __future__ import annotations
import json
import re
from urllib.parse import urlsplit
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

MAX_BYTES = 1024 * 1024
FORMATS = {'turtle', 'nt', 'xml', 'json-ld'}


def _check_contexts(value):
    pending = [value]
    count = 0
    while pending:
        node = pending.pop()
        count += 1
        if count > 10000:
            raise ValueError('Document structure exceeds limits')
        if isinstance(node, dict):
            if '@import' in node:
                raise ValueError('Remote JSON-LD context imports are forbidden')
            if '@context' in node:
                context = node['@context']
                values = context if isinstance(context, list) else [context]
                if any(isinstance(item, str) for item in values):
                    raise ValueError('Remote or file JSON-LD contexts are forbidden')
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)


def _subject_uri(value):
    if type(value) is not str or len(value) > 2048 or re.search(r'[\s<>"{}|\\^`]', value):
        raise ValueError('Invalid subject URI')
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https', 'urn'}:
        raise ValueError('Unsupported subject URI scheme')
    if parsed.scheme in {'http', 'https'} and (not parsed.netloc or parsed.username or parsed.password):
        raise ValueError('Invalid subject URI authority')
    if parsed.scheme == 'urn' and not parsed.path:
        raise ValueError('Invalid URN')
    return URIRef(value)


class OntologyDocument:
    """Full RDF graph, never a lossy classes/properties projection.

    Mutation methods return a fresh document. Internal native graphs must not
    cross platform API boundaries; serialize into platform-owned artifacts.
    """
    __slots__ = ('_graph',)

    def __init__(self, graph):
        self._graph = self._copy_graph(graph)

    @staticmethod
    def _copy_graph(graph):
        copied = Graph()
        for prefix, namespace in graph.namespaces():
            copied.bind(prefix, namespace)
        for triple in graph:
            copied.add(triple)
        return copied

    @classmethod
    def from_rdf(cls, data: str, *, format: str = 'turtle', base_uri: str | None = None):
        if type(data) is not str:
            raise ValueError('Document input must be text, not a path or URL')
        invalid_encoding = False
        size = 0
        try:
            size = len(data.encode('utf-8'))
        except UnicodeError:
            invalid_encoding = True
        if invalid_encoding or size > MAX_BYTES:
            raise ValueError('Document encoding or size exceeds limits')
        if format not in FORMATS:
            raise ValueError('Unsupported RDF format')
        if base_uri is not None:
            _subject_uri(base_uri)
        if format == 'xml' and re.search(r'<!\s*(?:DOCTYPE|ENTITY)', data, re.IGNORECASE):
            raise ValueError('XML DTD and entities are forbidden')
        if format == 'json-ld':
            decoded = None
            invalid_json = False
            try:
                decoded = json.loads(data)
            except (ValueError, RecursionError):
                invalid_json = True
            if invalid_json:
                raise ValueError('Invalid JSON-LD document')
            _check_contexts(decoded)
        graph = Graph()
        failed = False
        try:
            graph.parse(data=data, format=format, publicID=base_uri)
        except Exception:
            failed = True
        if failed:
            raise ValueError('Invalid RDF document')
        return cls(graph)

    def serialize(self, *, format: str = 'turtle') -> str:
        if format not in FORMATS:
            raise ValueError('Unsupported RDF format')
        result = self._graph.serialize(format=format)
        if type(result) is not str:
            raise ValueError('Unsupported RDF serialization result')
        return result

    def with_label(self, subject_uri: str, label: str, *, language: str | None = None):
        subject = _subject_uri(subject_uri)
        supported_types = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property}
        if not any((subject, RDF.type, kind) in self._graph for kind in supported_types):
            raise ValueError('Subject is not a supported named class or property')
        if type(label) is not str or not label.strip() or len(label) > 4096:
            raise ValueError('Invalid label')
        if language is not None and (type(language) is not str or not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', language)):
            raise ValueError('Invalid language tag')
        graph = self._copy_graph(self._graph)
        for old in list(graph.objects(subject, RDFS.label)):
            if isinstance(old, Literal) and old.language == language:
                graph.remove((subject, RDFS.label, old))
        graph.add((subject, RDFS.label, Literal(label, lang=language)))
        return type(self)(graph)
