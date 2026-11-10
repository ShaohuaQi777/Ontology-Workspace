"""Evidence contracts; never claim native capability via these unit tests."""
import importlib.metadata
import json
import pytest
from spikes.semantica.models import ProbeEvidence, installed_backend_version

# Isolates unit metadata lookup from heavy dependencies; native version is tested separately.
pytestmark = pytest.mark.usefixtures('backend_metadata')


def test_backend_version_reads_distribution_metadata():
    assert installed_backend_version() == importlib.metadata.version('semantica')


def test_missing_distribution_is_not_fabricated(monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, 'version', missing)
    assert installed_backend_version() is None


def test_evidence_is_json_serializable():
    evidence = ProbeEvidence(case_id='example', status='passed', backend_version='0.7.0',
                             api_symbol='semantica.example', run_id='run-test',
                             source_refs=['urn:technical:source'], checks={'expected_result': True})
    assert json.loads(evidence.model_dump_json())['case_id'] == 'example'


def test_passed_evidence_requires_native_symbol_source_and_checks():
    with pytest.raises(ValueError):
        ProbeEvidence(case_id='example', status='passed', backend_version='0.7.0',
                      api_symbol='', run_id='run-test', source_refs=[], checks={})


def test_passed_evidence_cannot_contain_failed_check():
    with pytest.raises(ValueError):
        ProbeEvidence(case_id='example', status='passed', backend_version='0.7.0',
                      api_symbol='semantica.example', run_id='run-test',
                      source_refs=['urn:technical:source'], checks={'expected_result': False})


def test_unavailable_evidence_requires_error_code():
    with pytest.raises(ValueError):
        ProbeEvidence(case_id='example', status='unavailable', backend_version=None,
                      api_symbol='', run_id='run-test')
