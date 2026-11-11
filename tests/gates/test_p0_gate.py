"""Execution evidence is not independent-review approval or product delivery."""
import importlib,json,subprocess,sys
from pathlib import Path
import pytest
from tests.spikes.test_gate import valid_report


def grading():
    return importlib.import_module('scripts.verify_a0').evaluate_p0_gate


def verification():
    return {'contract_exit_code':0,'clean_install_exit_code':0,'baseline_report_exit_code':0,'candidate_report_exit_code':0,'comparison':{'compatible':True},'baseline_environment':'env-a','candidate_environment':'env-b','backend_version':'0.7.0'}


def test_p0_requires_every_actual_execution_and_distinct_environment():
    evidence=valid_report(); value=verification()
    assert grading()(evidence,value)['passed']
    for key in ('contract_exit_code','clean_install_exit_code','baseline_report_exit_code','candidate_report_exit_code'):
        bad=dict(value); bad[key]=False
        assert not grading()(evidence,bad)['passed']
    bad=dict(value,candidate_environment='env-a'); assert not grading()(evidence,bad)['passed']
    bad=dict(value,comparison={'compatible':False}); assert not grading()(evidence,bad)['passed']
    bad=dict(value,backend_version='fake-contract'); assert not grading()(evidence,bad)['passed']


def test_caller_verdict_cannot_override_failed_native_evidence():
    value=dict(verification(),passed=True)
    evidence=valid_report(); evidence[0]['status']='failed'; evidence[0]['error_code']='BACKEND_FAILURE'
    assert not grading()(evidence,value)['passed']


def test_actual_p0_cli_runs_locked_isolation_and_current_version_comparison(tmp_path):
    root=Path(__file__).resolve().parents[2]
    evidence=root/'spikes/semantica/reports/0.7.0-ontologyworkspace.4/summary.json'
    result=subprocess.run([sys.executable,str(root/'scripts/verify_a0.py'),'--evidence',str(evidence),'--verify-p0'],cwd=root,capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value['passed'] and value['scope']=='g_p0_execution_only'
    assert value['release_approved'] is False
    assert value['baseline_environment']!=value['candidate_environment']
