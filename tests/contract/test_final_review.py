"""Small independent whole-branch finding reproductions, no real credentials."""
import hashlib,logging
import pytest
from ontology_platform.semantic import dto
from ontology_platform.semantic.errors import BackendError
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from tests.native_document.test_bounded_pdf import assemble


def source(root,name,data):
    if isinstance(data,str): data=data.encode()
    (root/name).write_bytes(data)
    return dto.ArtifactRef(path=name,sha256=hashlib.sha256(data).hexdigest(),size=len(data),kind='source',revision='v1')


def common():
    return {'run_id':'review-run','workspace_revision':'w1','source_refs':('source:s1',),'scope_ref':'scope:local'}


@pytest.mark.parametrize('field',['base_uri','subject_uri','source_refs','scope_ref'])
def test_credential_authorities_rejected_before_staging(tmp_path,field):
    uri='https://alice:TECHNICAL-CREDENTIAL-MARKER@example.invalid/Node'
    if field=='base_uri':
        ref=source(tmp_path,'graph.json','{"entities":[{"id":"n1","type":"Node","text":"Technical"}],"relationships":[]}')
        request=dto.OntologyRequest(**common(),source=ref,schema_revision='t1',action='generate')
        operation='ontology'; update={field:uri}
    elif field=='subject_uri':
        ref=source(tmp_path,'ontology.ttl','<urn:Node> a <http://www.w3.org/2002/07/owl#Class> .')
        request=dto.OntologyRequest(**common(),source=ref,schema_revision='t1',action='edit',subject_uri='urn:Node',label='Technical')
        operation='ontology'; update={field:uri}
    else:
        ref=source(tmp_path,'source.csv','id\nn1\n')
        request=dto.IngestRequest(**common(),source=ref,source_revision='v1',format='csv')
        operation='ingest'; update={field:('source:'+uri,) if field=='source_refs' else 'scope:'+uri}
    # Simulate transport bypass: boundary must revalidate, not trust frozen DTO.
    request=request.model_copy(update=update)
    with pytest.raises(BackendError) as caught: getattr(SemanticaBackend(tmp_path),operation)(request)
    assert caught.value.code=='INVALID_INPUT'
    assert not (tmp_path/'runs').exists()


def test_native_pdf_preflight_does_not_emit_raw_debug_metadata(tmp_path,caplog):
    marker='TECHNICAL-SECRET-REVIEW-MARKER'
    data=assemble([b'<< /Type /Catalog /Pages 2 0 R /PrivateMetadata ('+marker.encode()+b') >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>'])
    ref=source(tmp_path,'source.pdf',data)
    request=dto.ParseRequest(**common(),source=ref,source_revision='v1',format='pdf')
    with caplog.at_level(logging.DEBUG,logger='pdfminer'):
        result=SemanticaBackend(tmp_path).parse(request)
    assert result.data['pages']==1
    assert marker not in caplog.text


def test_relative_ontology_iris_bind_explicit_stable_base(tmp_path):
    ref=source(tmp_path,'source.ttl','<Node> a <http://www.w3.org/2002/07/owl#Class> .')
    request=dto.OntologyRequest(**common(),source=ref,schema_revision='t1',action='import',base_uri='https://example.invalid/ontology/')
    backend=SemanticaBackend(tmp_path)
    for _ in range(2):
        result=backend.ontology(request)
        tbox=next(item for item in result.artifact_refs if item.kind=='tbox')
        data=(tmp_path/tbox.path).read_text()
        assert '<https://example.invalid/ontology/Node>' in data
        assert 'file:' not in data
