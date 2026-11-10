"""Synthetic gate logic is not native execution evidence."""
import json
from pathlib import Path
import subprocess
import sys
from scripts.verify_a0 import REQUIRED_CASES, evaluate_contract_gate


def report():
    return [dict(case_id=name,status='passed',backend_version='0.7.0',api_symbol='semantica.test',
                 source_refs=['source:test'],checks={'check':True},error_code=None) for name in REQUIRED_CASES]


def test_contract_failure_rejects_otherwise_valid_native_gate():
    assert not evaluate_contract_gate(report(),1)['passed']


def test_contract_success_never_hides_native_failure():
    assert not evaluate_contract_gate([],0)['passed']


def test_both_pass_remains_partial_not_product_acceptance():
    result = evaluate_contract_gate(report(),0)
    assert result['passed']
    assert result['scope'] == 'native_and_contract_evidence_only'
    assert 'adapter_isolation' in result['not_yet_verified']


def test_actual_cli_runs_contract_suite():
    evidence = Path('spikes/semantica/reports/0.7.0-ontologyworkspace.3/summary.json')
    result = subprocess.run([sys.executable,'scripts/verify_a0.py','--evidence',str(evidence),'--verify-contracts'],capture_output=True,text=True)
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed['contract_exit_code'] == 0 and parsed['passed']
