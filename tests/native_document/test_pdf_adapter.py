"""Installed native extension/real Adapter evidence, not development patch imports."""
import hashlib
import importlib.metadata
import pytest
from ontology_platform.semantic.dto import ArtifactRef,ParseRequest
from ontology_platform.semantic.errors import BackendError
from ontology_platform.infrastructure.semantica_adapter.backend import SemanticaBackend
from test_bounded_pdf import pdf


def request(tmp_path,data):
    (tmp_path/'source.pdf').write_bytes(data)
    ref=ArtifactRef(path='source.pdf',sha256=hashlib.sha256(data).hexdigest(),size=len(data),kind='source',revision='s1')
    return ParseRequest(run_id='pdf1',workspace_revision='w1',source_refs=('source:s1',),scope_ref='scope:local',source=ref,source_revision='s1',format='pdf')


def test_installed_pdf_extension_version_and_native_adapter(tmp_path):
    from semantica.parse.bounded_pdf import BoundedPDFParser
    assert importlib.metadata.version('semantica')=='0.7.0+ontologyworkspace.5'
    req=request(tmp_path,pdf(compress=True))
    result=SemanticaBackend(tmp_path).parse(req)
    assert 'Native bounded PDF' in result.data['text']
    assert result.backend_version=='0.7.0+ontologyworkspace.5'
    assert result.artifact_refs


def test_pdf_expansion_rejected_before_any_snapshot(tmp_path):
    req=request(tmp_path,pdf('x'*300000,compress=True))
    with pytest.raises(BackendError) as caught: SemanticaBackend(tmp_path).parse(req)
    assert caught.value.code=='INVALID_INPUT'
    assert not (tmp_path/'runs').exists()
