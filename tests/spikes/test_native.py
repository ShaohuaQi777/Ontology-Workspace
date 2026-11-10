"""REAL Semantica acceptance cases. No metadata fixture, Fake, skip or xfail."""
import importlib.metadata
import pytest
from scripts.verify_a0 import REQUIRED_CASES
from spikes.semantica.runner import run_case


def test_version_is_installed_distribution_version():
    import json
    from pathlib import Path
    import semantica
    expected = json.loads(Path('patches/semantica/manifest.json').read_text())['version']
    assert importlib.metadata.version('semantica') == semantica.__version__ == expected


@pytest.mark.parametrize('case_id', REQUIRED_CASES)
def test_native_case(case_id, tmp_path):
    evidence = run_case(case_id, tmp_path)
    assert evidence.backend_version == importlib.metadata.version('semantica')
    assert evidence.status == 'passed', f'{case_id}: {evidence.error_code}'
    assert evidence.api_symbol.startswith('semantica.')
    assert evidence.source_refs
    assert evidence.artifact_hashes
    assert evidence.checks['native_api_invoked'] is True
