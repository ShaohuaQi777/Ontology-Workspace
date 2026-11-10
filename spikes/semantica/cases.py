"""Actual native probes. RDFLib is used only for output assertions, not a fallback engine."""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3

from scripts.verify_a0 import REQUIRED_CASES
from .fixtures import GRAPH, COMPLEX_TTL, SHAPES, make_pdf, make_docx


class NativeAPIUnavailable(Exception):
    pass


def not_implemented(output_dir: Path) -> dict:
    raise NotImplementedError('Native probe implementation pending')


def record(work, case_id, symbol, payload, checks, inputs=(), format='json'):
    output = work / 'result.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')
    return {'api_symbol': symbol, 'source_refs': [f'urn:technical-probe:{case_id}'],
            'parameters': {'format': format}, 'checks': {'native_api_invoked': True, **checks},
            'artifacts': {'result': output, **{path.name: path for path in inputs}}}


def ingest_csv(work):
    from semantica.ingest.file_ingestor import FileIngestor
    from semantica.parse.csv_parser import CSVParser
    path = work / 'technical.csv'
    path.write_bytes(b'id,value\nn1,7\n')
    ingested = FileIngestor().ingest_file(path, read_content=True)
    parsed = CSVParser().parse(path, has_header=True, encoding='utf-8')
    return record(work, 'ingest_csv', 'semantica.parse.csv_parser.CSVParser.parse',
                  {'headers': parsed.headers, 'rows': parsed.rows, 'row_count': parsed.row_count},
                  {'original_bytes': ingested.content == path.read_bytes(), 'file_type': ingested.file_type == 'csv',
                   'headers': parsed.headers == ['id', 'value'], 'rows': parsed.rows == [{'id': 'n1', 'value': '7'}],
                   'row_count': parsed.row_count == 1}, [path], 'csv')


def ingest_json(work):
    from semantica.ingest.file_ingestor import FileIngestor
    from semantica.parse.json_parser import JSONParser
    path = work / 'technical.json'
    path.write_text('{"id":"n1","value":7}', encoding='utf-8')
    ingested = FileIngestor().ingest_file(path, read_content=True)
    parsed = JSONParser().parse(path, flatten=False, extract_paths=False, encoding='utf-8')
    return record(work, 'ingest_json', 'semantica.parse.json_parser.JSONParser.parse',
                  {'type': parsed.type, 'data': parsed.data},
                  {'original_bytes': ingested.content == path.read_bytes(), 'object_type': parsed.type == 'object',
                   'data': parsed.data == {'id': 'n1', 'value': 7}}, [path])


def ingest_sqlite(work):
    import sqlalchemy  # Confirm required dependency before native wrapper can hide it.
    from semantica.ingest.db_ingestor import DBIngestor
    path = work / 'technical.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE item(id TEXT PRIMARY KEY, value INTEGER)')
        connection.execute('INSERT INTO item VALUES (?, ?)', ('n1', 7))
    url = f'sqlite:///file:{path}?mode=ro&uri=true'
    native = DBIngestor(fail_fast=True)
    result = native.ingest_database(url, include_tables=['item'], max_rows_per_table=1)
    table = result['tables']['item']
    rows = table['rows']
    return record(work, 'ingest_sqlite', 'semantica.ingest.db_ingestor.DBIngestor.ingest_database',
                  {'total_tables': result['total_tables'], 'rows': rows, 'row_count': table['row_count']},
                  {'tables': result['total_tables'] == 1, 'rows': rows == [{'id': 'n1', 'value': 7}],
                   'row_count': table['row_count'] == 1}, [path], 'sqlite')


def parse_pdf(work):
    from semantica.parse.pdf_parser import PDFParser
    path = make_pdf(work / 'technical.pdf')
    result = PDFParser().parse(path, extract_text=True, extract_tables=False, extract_images=False)
    return record(work, 'parse_pdf', 'semantica.parse.pdf_parser.PDFParser.parse',
                  {'text': result['full_text'], 'pages': result['total_pages'], 'metadata': result['metadata']},
                  {'text': 'Probe text' in result['full_text'], 'pages': result['total_pages'] == 1,
                   'page_number': result['pages'][0]['page_number'] == 1,
                   'metadata_page_count': result['metadata']['page_count'] == 1}, [path], 'pdf')


def parse_docx(work):
    from semantica.parse.docx_parser import DOCXParser
    path = make_docx(work / 'technical.docx')
    result = DOCXParser().parse(path, extract_tables=False, extract_comments=False, extract_formatting=False)
    return record(work, 'parse_docx', 'semantica.parse.docx_parser.DOCXParser.parse',
                  {'text': result['full_text'], 'paragraphs': result['paragraphs']},
                  {'text': result['full_text'] == 'Probe text', 'paragraphs': result['paragraphs'] == ['Probe text'],
                   'count': result['total_paragraphs'] == 1, 'tables': result['total_tables'] == 0}, [path], 'docx')


def build_graph(work):
    from semantica.kg.graph_builder import GraphBuilder
    result = GraphBuilder(merge_entities=False, resolve_conflicts=False, graph_store=None).build(GRAPH, extract=False)
    return record(work, 'build_graph', 'semantica.kg.graph_builder.GraphBuilder.build', result,
                  {'entity_ids': {entity['id'] for entity in result['entities']} == {'n1', 'n2'},
                   'relationships': result['relationships'] == GRAPH['relationships'],
                   'entity_count': result['metadata']['num_entities'] == 2,
                   'relation_count': result['metadata']['num_relationships'] == 1,
                   'no_resolution': result['metadata']['entity_resolution_applied'] is False})


def ontology_generate(work):
    from semantica.ontology.ontology_generator import OntologyGenerator
    from semantica.ontology.owl_generator import OWLGenerator
    ontology = OntologyGenerator(base_uri='https://example.invalid/ontology/', min_occurrences=1).generate_ontology(
        GRAPH, name='ProbeOntology', min_occurrences=1, build_hierarchy=False, validate=False)
    ttl = OWLGenerator().generate_owl(ontology, format='turtle')
    path = work / 'generated.ttl'
    path.write_text(ttl, encoding='utf-8')
    classes = ontology['classes']
    properties = ontology['properties']
    nodes = [item for item in classes if item.get('name') == 'Node']
    links = [item for item in properties if item.get('metadata', {}).get('inferred_from') == 'linksTo']
    payload = {'name': ontology['name'], 'uri': ontology['uri'], 'classes': classes,
               'properties': properties, 'imports': ontology.get('imports', [])}
    return record(work, 'ontology_generate', 'semantica.ontology.ontology_generator.OntologyGenerator.generate_ontology',
                  payload, {'name': ontology['name'] == 'ProbeOntology', 'class': bool(nodes),
                            'class_count': bool(nodes) and nodes[0]['entity_count'] == 2,
                            'property': bool(links), 'no_imports': ontology.get('imports', []) == [],
                            'owl_output': bool(ttl)}, [path], 'turtle')


def ontology_roundtrip(work):
    from semantica.ontology.document import OntologyDocument
    from rdflib import BNode, Graph, URIRef
    from rdflib.compare import isomorphic
    from rdflib.namespace import OWL
    path = work / 'complex.ttl'
    path.write_text(COMPLEX_TTL, encoding='utf-8')
    data = OntologyDocument.from_rdf(COMPLEX_TTL, format='turtle')
    exported = data.serialize(format='turtle')
    output = work / 'roundtrip.ttl'
    output.write_text(exported, encoding='utf-8')
    source_graph = Graph().parse(data=COMPLEX_TTL, format='turtle')
    result_graph = Graph().parse(data=exported, format='turtle')
    return record(work, 'ontology_roundtrip', 'semantica.ontology.document.OntologyDocument.serialize',
                  {'input_triples': len(source_graph), 'output_triples': len(result_graph)},
                  {'isomorphic': isomorphic(source_graph, result_graph),
                   'blank_nodes': any(isinstance(node, BNode) for triple in result_graph for node in triple),
                   'imports': (URIRef('https://example.invalid/probe/'), OWL.imports,
                               URIRef('https://example.invalid/not-authorized')) in result_graph}, [path, output], 'turtle')


def ontology_edit(work):
    from semantica.ontology.document import OntologyDocument
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDFS
    from rdflib.compare import isomorphic
    original = OntologyDocument.from_rdf(COMPLEX_TTL)
    edited = original.with_label('https://example.invalid/probe/Node', 'Changed technical label')
    before = Graph().parse(data=COMPLEX_TTL, format='turtle')
    expected = Graph().parse(data=COMPLEX_TTL, format='turtle')
    subject = URIRef('https://example.invalid/probe/Node')
    expected.remove((subject, RDFS.label, Literal('Technical node')))
    expected.add((subject, RDFS.label, Literal('Changed technical label')))
    after = Graph().parse(data=edited.serialize(), format='turtle')
    output = work / 'edited.ttl'
    output.write_text(edited.serialize(), encoding='utf-8')
    return record(work, 'ontology_edit', 'semantica.ontology.document.OntologyDocument.with_label',
                  {'input_triples': len(before), 'output_triples': len(after)},
                  {'label_only': isomorphic(expected, after),
                   'original_unchanged': isomorphic(before, Graph().parse(data=original.serialize(), format='turtle'))},
                  [output], 'turtle')


def shacl(work, expect_conforms):
    from semantica.ontology.ontology_validator import run_shacl_validation
    case_id = 'shacl_pass' if expect_conforms else 'shacl_fail'
    predicate = 'p' if expect_conforms else 'q'
    data = f'@prefix ex: <https://example.invalid/> . ex:n1 ex:{predicate} "v" .'
    shape = work / 'shapes.ttl'
    shape.write_text(SHAPES, encoding='utf-8')
    source = work / 'data.ttl'
    source.write_text(data, encoding='utf-8')
    result = run_shacl_validation(data, SHAPES)
    checks = {'conforms': result.conforms is expect_conforms,
              'count': result.violation_count == (0 if expect_conforms else 1)}
    if not expect_conforms:
        violation = result.violations[0]
        checks.update({'focus_node': violation.focus_node == 'https://example.invalid/n1',
                       'path': violation.result_path == 'https://example.invalid/p',
                       'constraint': violation.constraint == 'MinCountConstraintComponent',
                       'min_count': violation.min_count == 1, 'raw_report': bool(result.raw_report)})
    return record(work, case_id, 'semantica.ontology.ontology_validator.run_shacl_validation',
                  {'conforms': result.conforms, 'violations': [item.to_dict() for item in result.violations]},
                  checks, [shape, source], 'turtle')


def reason_forward(work):
    from semantica.reasoning.reasoner import Reasoner, Rule
    asserted = ['Token(x)']
    rules = [Rule(rule_id='r1', name='token_to_mark', conditions=['Token(?x)'], conclusion='Mark(?x)')]
    inferred = Reasoner(max_iterations=1).infer_with_results(asserted, rules)
    results = [{'conclusion': item.conclusion, 'rule_id': item.rule_used.rule_id,
                'premises': item.premises, 'confidence': item.confidence} for item in inferred]
    source = work / 'asserted.json'
    source.write_text(json.dumps(asserted), encoding='utf-8')
    return record(work, 'reason_forward', 'semantica.reasoning.reasoner.Reasoner.infer_with_results',
                  {'asserted': asserted, 'inferred': results},
                  {'conclusion': [item['conclusion'] for item in results] == ['Mark(x)'],
                   'rule': bool(results) and results[0]['rule_id'] == 'r1',
                   'premises': bool(results) and results[0]['premises'] == ['Token(x)'],
                   'separate': not set(asserted) & {item['conclusion'] for item in results}}, [source])


def conflict_evidence(work):
    from semantica.conflicts.conflict_detector import ConflictDetector
    inputs = [{'id': 'n1', 'value': value, 'source': source, 'page': page,
               'confidence': 1.0, 'metadata': {'quote': value}}
              for value, source, page in [('A', 'src-a', 1), ('B', 'src-b', 2)]]
    conflicts = ConflictDetector(track_provenance=True, auto_resolve=False).detect_value_conflicts(inputs, 'value')
    payload = [{'type': item.conflict_type.name, 'entity_id': item.entity_id, 'property': item.property_name,
                'values': item.conflicting_values,
                'sources': [{'document': source['document'], 'page': source['page'],
                             'quote': source['metadata'].get('quote')} for source in item.sources]} for item in conflicts]
    return record(work, 'conflict_evidence', 'semantica.conflicts.conflict_detector.ConflictDetector.detect_value_conflicts',
                  payload, {'count': len(payload) == 1, 'type': bool(payload) and payload[0]['type'] == 'VALUE_CONFLICT',
                            'values': bool(payload) and set(payload[0]['values']) == {'A', 'B'},
                            'sources': bool(payload) and len(payload[0]['sources']) == 2})


def provenance_export(work):
    from semantica.provenance.manager import ProvenanceManager
    from semantica.provenance.storage import InMemoryStorage
    from rdflib import Graph, Namespace, RDF, URIRef
    manager = ProvenanceManager(storage=InMemoryStorage())
    initial = manager.track_entity('input', 'probe:text')
    derived = manager.track_entity('output', 'input', parent_entity_id='input', used_entities=['input'],
                                   activity_id='extract', agent_id='native-probe')
    ttl = manager.export_prov(format='turtle', base_uri='urn:probe:')
    output = work / 'provenance.ttl'
    output.write_text(ttl, encoding='utf-8')
    graph = Graph().parse(data=ttl, format='turtle')
    prov = Namespace('http://www.w3.org/ns/prov#')
    inp, out, activity, agent = [URIRef('urn:probe:' + item) for item in ['input', 'output', 'extract', 'native-probe']]
    return record(work, 'provenance_export', 'semantica.provenance.manager.ProvenanceManager.export_prov',
                  {'triple_count': len(graph)},
                  {'stored': initial is not None and derived is not None, 'entity': (out, RDF.type, prov.Entity) in graph,
                   'derived': (out, prov.wasDerivedFrom, inp) in graph,
                   'generated': (out, prov.wasGeneratedBy, activity) in graph,
                   'used': (activity, prov.used, inp) in graph,
                   'agent': (out, prov.wasAttributedTo, agent) in graph}, [output], 'turtle')


def normalize_align(work):
    from semantica.normalize.text_normalizer import TextNormalizer
    from semantica.normalize.entity_normalizer import EntityNormalizer
    normalized = TextNormalizer().normalize_text('e\u0301')
    links = EntityNormalizer(alias_map={'node-a': 'Canonical Node'}).link_entities([' NODE-A ', 'node-a'])
    return record(work, 'normalize_align', 'semantica.normalize.entity_normalizer.EntityNormalizer.link_entities',
                  {'normalized': normalized, 'aliases': links, 'alignment_kind': 'explicit_alias_map',
                   'cross_ontology_semantics': False},
                  {'unicode': normalized == 'é', 'aliases': set(links.values()) == {'Canonical Node'},
                   'source_keys': set(links) == {' NODE-A ', 'node-a'}})


def extract_entities_relations_events(work):
    from semantica.semantic_extract.methods import extract_entities_ml, extract_relations_dependency
    from semantica.semantic_extract.event_detector import EventDetector
    text = 'Alice released Atlas in Paris in 2024.'
    entities = extract_entities_ml(text, model='en_core_web_sm')
    relations = extract_relations_dependency(text, entities, model='en_core_web_sm')
    events = EventDetector(method='pattern').detect_events(text)
    payload = {'text': text, 'entities': [asdict(item) for item in entities],
               'relations': [asdict(item) for item in relations], 'events': [asdict(item) for item in events],
               'event_method': 'fixed_native_keyword_patterns_not_llm'}
    return record(work, 'extract_entities_relations_events', 'semantica.semantic_extract.methods.extract_entities_ml',
                  payload, {'entities': len(entities) >= 2,
                            'entity_spans': bool(entities) and all(text[e.start_char:e.end_char] == e.text for e in entities),
                            'ml_provenance': bool(entities) and all(e.metadata.get('extraction_method') == 'ml' for e in entities),
                            'relations': bool(relations) and all(r.predicate for r in relations),
                            'dependency_provenance': bool(relations) and all(r.metadata.get('extraction_method') == 'dependency' for r in relations),
                            'events': bool(events) and any(event.event_type == 'launch' for event in events)})


def query_select_ask(work):
    from semantica.triplet_store.triplet_store import TripletStore
    from semantica.reasoning.sparql_reasoner import SPARQLReasoner
    from semantica.semantic_extract.types import Triplet
    from .query_safety import validate_readonly_sparql
    store = TripletStore(backend='oxigraph', path=None)
    store.add_triplets([Triplet('urn:probe:s', 'urn:probe:p', 'urn:probe:o')])
    native = SPARQLReasoner(triplet_store=store, enable_inference=False)
    select = native.execute_query(validate_readonly_sparql('SELECT ?o WHERE { <urn:probe:s> <urn:probe:p> ?o }'))
    positive = native.execute_query(validate_readonly_sparql('ASK WHERE { <urn:probe:s> <urn:probe:p> <urn:probe:o> }'))
    negative = native.execute_query(validate_readonly_sparql('ASK WHERE { <urn:probe:s> <urn:probe:p> <urn:probe:missing> }'))
    bindings = select.bindings
    return record(work, 'query_select_ask', 'semantica.reasoning.sparql_reasoner.SPARQLReasoner.execute_query',
                  {'variables': select.variables, 'bindings': bindings,
                   'ask_true': positive.metadata.get('boolean'), 'ask_false': negative.metadata.get('boolean')},
                  {'variables': select.variables == ['o'], 'row_count': len(bindings) == 1,
                   'native_uri_binding': bool(bindings) and bindings[0]['o'] == {'type': 'uri', 'value': 'urn:probe:o'},
                   'ask_true': positive.metadata.get('boolean') is True,
                   'ask_false': negative.metadata.get('boolean') is False})


CASES = {case_id: not_implemented for case_id in REQUIRED_CASES}
CASES.update({name: globals()[name] for name in REQUIRED_CASES if name in globals()})
CASES['shacl_pass'] = lambda work: shacl(work, True)
CASES['shacl_fail'] = lambda work: shacl(work, False)
