"""Native-only child entry point. SDK logs never enter platform responses."""
import hashlib
import json
import logging
import os
import resource
from .secure_io import Directory, MAX_BYTES
from .input_policy import graph_input, GRAPH_FIELDS
from pathlib import Path
import re
import sys
from ...semantic.errors import BackendError, ERROR_MESSAGES
from .translation import to_platform_value


def extract_native(text):
    import spacy
    from semantica.semantic_extract import methods
    # Prove the fixed CPU model is available; do not accept silent pattern fallback.
    spacy.load('en_core_web_sm')
    entities = methods.extract_entities_ml(text,model='en_core_web_sm')
    relations = methods.extract_relations_dependency(text,entities,model='en_core_web_sm')
    if any(item.metadata.get('extraction_method') != 'ml' for item in entities):
        raise ImportError('ML extraction unavailable')
    if any(item.metadata.get('extraction_method') != 'dependency' for item in relations):
        raise ImportError('Dependency extraction unavailable')
    projected_entities = [{'text':item.text,'label':item.label,'start':item.start_char,'end':item.end_char,
                           'confidence':item.confidence,'state':'DRAFT','method':'ml'} for item in entities]
    projected_relations = [{'subject':item.subject.text,'predicate':item.predicate,'object':item.object.text,
                            'confidence':item.confidence,'state':'DRAFT','method':'dependency'} for item in relations]
    return {'entities':projected_entities,'relations':projected_relations,'events':[],
            'model':'en_core_web_sm','limitations':['Event extraction is not part of this request']}


ATOM = re.compile(r'^([A-Za-z][A-Za-z0-9_]*)\(([?A-Za-z0-9_,:-]+)\)$')

def checked_rules(facts,rules):
    if type(facts) is not list or type(rules) is not list or len(facts)>1000 or not 1<=len(rules)<=128:
        raise ValueError('Invalid finite rule input')
    arities={}; constants=set(); condition_counts=[]
    def atom(text):
        if type(text) is not str or len(text)>1024:
            raise ValueError('Invalid atom')
        match=ATOM.fullmatch(text)
        if not match:
            raise ValueError('Only positive finite atoms are supported')
        arguments=match[2].split(',')
        if any(not re.fullmatch(r'\?[A-Za-z_][A-Za-z0-9_]*|[A-Za-z0-9_:-]+',part) for part in arguments):
            raise ValueError('Invalid native-compatible argument')
        if match[1] in arities and arities[match[1]] != len(arguments):
            raise ValueError('Inconsistent predicate arity')
        variables=[part for part in arguments if part.startswith('?')]
        if len(set(variables))!=len(variables) or len(arguments)>4:
            raise ValueError('Unsupported native atom binding')
        constants.update(part for part in arguments if not part.startswith('?'))
        arities[match[1]]=len(arguments)
        return match[1],set(variables)
    for fact in facts:
        _,variables=atom(fact)
        if variables:
            raise ValueError('Facts must be ground')
    dependencies={}; ids=set()
    for rule in rules:
        if type(rule) is not dict or set(rule)!={'id','conditions','conclusion'} or type(rule['id']) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',rule['id']) or rule['id'] in ids:
            raise ValueError('Invalid rule record')
        ids.add(rule['id'])
        if type(rule['conditions']) is not list or not 1<=len(rule['conditions'])<=16:
            raise ValueError('Invalid rule conditions')
        conclusion,used=atom(rule['conclusion']); bound=set(); predicates=set()
        for condition in rule['conditions']:
            predicate,variables=atom(condition); bound|=variables; predicates.add(predicate)
        if not used<=bound:
            raise ValueError('Unbound rule variables')
        dependencies.setdefault(conclusion,set()).update(predicates)
        condition_counts.append(len(rule['conditions']))
    # Upper-bound the finite ground universe and worst-case native Cartesian matching.
    universe=sum(max(len(constants),1)**arity for arity in arities.values())
    if len(facts)>64 or len(rules)>16 or universe>128 or any(universe**count>4096 for count in condition_counts) or sum(universe**count for count in condition_counts)>16384:
        raise ValueError('Native rule matching exceeds computational budget')
    visiting=set(); finished=set()
    def visit(predicate):
        if predicate in visiting: raise ValueError('Recursive rules unsupported')
        if predicate in finished: return
        visiting.add(predicate)
        for requirement in dependencies.get(predicate,()): visit(requirement)
        visiting.remove(predicate); finished.add(predicate)
    for predicate in dependencies: visit(predicate)


def execute(operation,request,paths,work):
    source=work/paths['source']; artifacts=[]
    if operation=='ingest':
        from semantica.ingest.file_ingestor import FileIngestor
        native=FileIngestor().ingest_file(source,read_content=True)
        if native.content != source.read_bytes(): raise RuntimeError('Native ingest lost source bytes')
        return {'file_type':native.file_type,'size':source.stat().st_size},artifacts
    if operation=='parse':
        format=request['format']
        if format=='csv':
            from semantica.parse.csv_parser import CSVParser
            value=CSVParser().parse(source,has_header=True,encoding='utf-8')
            return {'headers':value.headers,'rows':value.rows,'row_count':value.row_count},artifacts
        if format=='json':
            from semantica.parse.json_parser import JSONParser
            value=JSONParser().parse(source,flatten=False,extract_paths=False,encoding='utf-8')
            return {'type':value.type,'content':value.data},artifacts
        if format=='pdf':
            from semantica.parse.bounded_pdf import BoundedPDFParser
            value=BoundedPDFParser().parse(source)
            return {'text':value['text'],'pages':value['pages']},artifacts
        from semantica.parse.docx_parser import DOCXParser
        value=DOCXParser().parse(source,extract_tables=False,extract_comments=False,extract_formatting=False)
        return {'text':value['full_text'],'paragraphs':value['paragraphs']},artifacts
    if operation=='extract':
        return extract_native(source.read_text(encoding='utf-8')),artifacts
    if operation=='build_graph':
        from semantica.kg.graph_builder import GraphBuilder
        graph=json.loads(source.read_text(encoding='utf-8'))
        if type(graph) is not dict or set(graph)!={'entities','relationships'}:
            raise ValueError('Invalid graph input')
        for key,allowed in [('entities',{'id','type','text'}),('relationships',{'source','target','type'})]:
            if type(graph[key]) is not list or len(graph[key])>1000:
                raise ValueError('Invalid graph records')
            for record in graph[key]:
                if type(record) is not dict or not set(record)<=allowed or not all(type(item) is str and len(item)<=4096 for item in record.values()):
                    raise ValueError('Unsupported graph fields')
        value=GraphBuilder(merge_entities=False,resolve_conflicts=False,graph_store=None).build(graph,extract=False)
        output={}
        for key,allowed in [('entities',{'id','type','text'}),('relationships',{'source','target','type'})]:
            output[key]=[{**{name:item[name] for name in allowed if name in item},'state':'DRAFT','confidence':None} for item in value[key]]
        return output,artifacts
    if operation=='ontology':
        from semantica.ontology.document import OntologyDocument
        if request['action']=='generate':
            from semantica.ontology.ontology_generator import OntologyGenerator
            from semantica.ontology.owl_generator import OWLGenerator
            graph=json.loads(source.read_text(encoding='utf-8'))
            value=OntologyGenerator(base_uri=request['base_uri'],min_occurrences=1).generate_ontology(graph,name=request['name'],min_occurrences=1,build_hierarchy=False,validate=False)
            ttl=OWLGenerator().generate_owl(value,format='turtle')
            document=OntologyDocument.from_rdf(ttl)
        else:
            document=OntologyDocument.from_rdf(source.read_text(encoding='utf-8'),format=request['format'],base_uri=request['base_uri'])
            if request['action']=='edit':
                if not request['subject_uri'] or request['label'] is None: raise ValueError('Missing label edit fields')
                document=document.with_label(request['subject_uri'],request['label'],language=request['language'])
        encoded=document.serialize(format='nt').encode('utf-8')
        if len(encoded)>MAX_BYTES: raise ValueError('Ontology output exceeds budget')
        with Directory.root(work) as directory: directory.write('ontology.nt',encoded)
        artifacts.append(['ontology.nt','tbox'])
        return {'format':'nt','state':'DRAFT','action':request['action']},artifacts
    if operation=='validate_shacl':
        from semantica.ontology.document import OntologyDocument
        from semantica.ontology.ontology_validator import run_shacl_validation
        graph=OntologyDocument.from_rdf(source.read_text(encoding='utf-8'),base_uri='urn:ontology-workspace:data:'+request['source']['sha256']+':').serialize()
        shapes_document=OntologyDocument.from_rdf((work/paths['shapes']).read_text(encoding='utf-8'),base_uri='urn:ontology-workspace:shapes:'+request['shapes']['sha256']+':')
        sh='http://www.w3.org/ns/shacl#'
        allowed={'targetNode','targetClass','targetSubjectsOf','targetObjectsOf','property','path','minCount','maxCount',
                 'datatype','class','nodeKind','pattern','flags','minLength','maxLength','minInclusive','maxInclusive',
                 'minExclusive','maxExclusive','hasValue','in','closed','ignoredProperties','node','and','or','not','xone',
                 'severity','message','name','description','order','deactivated','alternativePath','inversePath',
                 'zeroOrMorePath','oneOrMorePath','zeroOrOnePath','qualifiedValueShape','qualifiedMinCount','qualifiedMaxCount',
                 'qualifiedValueShapesDisjoint','equals','disjoint','lessThan','lessThanOrEquals','languageIn','uniqueLang'}
        for _,predicate,_ in shapes_document._graph:
            name=str(predicate)
            if name == 'http://www.w3.org/2002/07/owl#imports' or (name.startswith(sh) and name[len(sh):] not in allowed):
                raise BackendError('UNSUPPORTED_CAPABILITY',ERROR_MESSAGES['UNSUPPORTED_CAPABILITY'],request['run_id'],False)
        shapes=shapes_document.serialize()
        value=run_shacl_validation(graph,shapes)
        findings=[item.to_dict() for item in [*value.violations,*value.warnings,*value.infos]]
        return {'conforms':value.conforms,'violations':[item.to_dict() for item in value.violations],'findings':findings},artifacts
    if operation=='reason':
        from semantica.reasoning.reasoner import Reasoner,Rule
        facts=json.loads(source.read_text(encoding='utf-8')); rules=json.loads((work/paths['rules']).read_text(encoding='utf-8'))
        checked_rules(facts,rules)
        native_rules=[Rule(rule_id=rule['id'],name=rule['id'],conditions=rule['conditions'],conclusion=rule['conclusion']) for rule in rules]
        inferred=Reasoner(max_iterations=len(rules)+1).infer_with_results(facts,native_rules)
        def fact_ref(value): return 'fact:'+request['graph_revision']+':'+hashlib.sha256(value.encode()).hexdigest()
        rows=[{'conclusion':item.conclusion,'rule_version':request['ruleset_revision']+':'+item.rule_used.rule_id,
               'premise_refs':[fact_ref(premise) for premise in item.premises],'confidence':None,'state':'DRAFT'} for item in inferred]
        return {'asserted':facts,'inferred':rows},artifacts
    raise NotImplementedError('Unsupported native operation')


def persist_response(work,response):
    encoded=json.dumps(response,allow_nan=False).encode('utf-8')
    if len(encoded)>MAX_BYTES: raise ValueError('Result output exceeds budget')
    with Directory.root(work) as directory: directory.write('response.json',encoded)


def main():
    if len(sys.argv)!=3 or sys.argv[1]!='--directory-fd': raise ValueError('Directory capability required')
    os.fchdir(int(sys.argv[2]))
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))
    resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_BYTES,MAX_BYTES))
    logging.disable(logging.CRITICAL)
    from loguru import logger
    logger.remove()
    work=Path('.')
    with Directory(os.dup(int(sys.argv[2]))) as directory:
        job=json.loads(directory.read('request.json'))
    request=job['request']
    try:
        data,artifacts=execute(job['operation'],request,job['paths'],work)
        response={'data':to_platform_value(data,run_id=request['run_id']),'artifacts':artifacts}
    except BackendError as safe:
        response={'error':safe.to_dict()}
    except Exception as native:
        error=BackendError.from_native(native,request['run_id'])
        response={'error':error.to_dict()}
    try:
        persist_response(work,response)
    except ValueError:
        persist_response(work,{'error':BackendError('BACKEND_FAILURE',ERROR_MESSAGES['BACKEND_FAILURE'],request['run_id'],False).to_dict()})


if __name__=='__main__': main()
