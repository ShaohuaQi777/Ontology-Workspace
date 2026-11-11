"""Genuine installed PDF preflight through scoped registration, without parent leaks."""
import importlib.util,logging
from pathlib import Path
import pytest
from sqlalchemy import text
from test_workspaces import workspace


def fixtures():
    path=Path(__file__).resolve().parents[1]/'native_document/test_bounded_pdf.py'
    spec=importlib.util.spec_from_file_location('workspace_pdf_fixtures',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_scoped_pdf_registration_quiet_and_original_bytes_preserved(tmp_path,caplog):
    work,accounts,store,actor,root=workspace(tmp_path); project=work.create_project(actor,'PDF','urn:pdf:')
    sample=fixtures()
    # Fixed technical private value in a valid zero-page PDF, never a live credential.
    objects=[b'<< /Type /Catalog /Pages 2 0 R /PrivateMetadata (TECHNICAL-PRIVATE-PDF-MARKER) >>',b'<< /Type /Pages /Kids [] /Count 0 >>']
    data=sample.assemble(objects)
    with caplog.at_level(logging.DEBUG): source=work.register_source(actor,project.project_id,'pdf',data)
    assert 'TECHNICAL-PRIVATE-PDF-MARKER' not in caplog.text
    assert work.read_source(actor,project.project_id,source.source_id)==data
    store.close()


@pytest.mark.parametrize('kind',['orphan','expansion'])
def test_native_pdf_budget_failure_leaves_no_registered_source_or_file(tmp_path,kind):
    work,accounts,store,actor,root=workspace(tmp_path); project=work.create_project(actor,'PDF','urn:pdf:')
    sample=fixtures()
    if kind=='orphan': data=sample.assemble([b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [] /Count 0 >>']+[b'<< /Type /Page /MediaBox [0 0 100 100] >>']*65)
    else: data=sample.pdf('x'*300000,compress=True)
    assert len(data)<10000
    with pytest.raises(Exception) as invalid: work.register_source(actor,project.project_id,'pdf',data)
    assert invalid.value.code=='INVALID_SOURCE' and not list(root.iterdir())
    with store.transaction() as connection: assert connection.execute(text('SELECT COUNT(*) FROM sources')).scalar_one()==0
    store.close()
