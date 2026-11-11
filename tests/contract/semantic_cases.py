"""Domain-neutral contract inputs shared by genuine SDK and test double."""
import hashlib,json
from ontology_platform.semantic import dto

OPERATIONS=('ingest','parse','extract','build_graph','ontology','validate_shacl','reason')
RESULTS=dict(zip(OPERATIONS,(dto.IngestResult,dto.ParseResult,dto.ExtractionResult,dto.GraphResult,dto.OntologyResult,dto.ValidationResult,dto.ReasoningResult)))


def artifact(root,name,text):
    data=text.encode(); (root/name).write_bytes(data)
    return dto.ArtifactRef(path=name,sha256=hashlib.sha256(data).hexdigest(),size=len(data),kind='source',revision='v1')


def request(root,operation):
    common={'run_id':'shared-'+operation,'workspace_revision':'w1','source_refs':('source:s1',),'scope_ref':'scope:local'}
    if operation in ('ingest','parse'):
        source=artifact(root,'source.csv','id,value\nn1,7\n')
        cls=dto.IngestRequest if operation=='ingest' else dto.ParseRequest
        return cls(**common,source=source,source_revision='v1',format='csv')
    if operation=='extract':
        return dto.ExtractRequest(**common,source=artifact(root,'source.txt','Apple acquired Microsoft in California.'),source_revision='v1')
    if operation=='build_graph':
        source=artifact(root,'source.json',json.dumps({'entities':[{'id':'n1','type':'Node','text':'Technical node'}],'relationships':[]}))
        return dto.GraphBuildRequest(**common,source=source,graph_revision='g1')
    if operation=='ontology':
        return dto.OntologyRequest(**common,source=artifact(root,'source.ttl','@prefix owl: <http://www.w3.org/2002/07/owl#> . _:n a owl:Class .'),schema_revision='t1',action='import')
    if operation=='validate_shacl':
        source=artifact(root,'source.ttl','<urn:n> <urn:p> "v" .')
        shapes=artifact(root,'shapes.ttl','@prefix sh: <http://www.w3.org/ns/shacl#> . <urn:S> a sh:NodeShape ; sh:targetNode <urn:n> ; sh:property [ sh:path <urn:p> ; sh:minCount 2 ] .')
        return dto.SHACLRequest(**common,source=source,shapes=shapes,graph_revision='g1',shapes_revision='s1',suite_revision='q1')
    source=artifact(root,'source.json','["Token(x)"]')
    rules=artifact(root,'rules.json',json.dumps([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Mark(?x)'}]))
    return dto.ReasoningRequest(**common,source=source,rules=rules,graph_revision='g1',ruleset_revision='rules:v1')
