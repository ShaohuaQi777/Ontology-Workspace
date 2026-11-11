"""Run the real native report producer; fixed test fixtures are not SDK proof."""
import importlib,json,subprocess,sys
from pathlib import Path


def test_native_report_records_installed_version_inputs_and_real_failures(tmp_path):
    script=Path(__file__).resolve().parents[2]/'scripts/record_semantic_contract.py'
    output=tmp_path/'report.json'
    result=subprocess.run([sys.executable,str(script),'--workdir',str(tmp_path/'cases'),'--output',str(output)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stderr
    value=json.loads(output.read_text())
    assert value['backend_kind']=='real' and value['backend_version']=='0.7.0+ontologyworkspace.5'
    assert len(value['cases'])==15
    assert value['cases']['reason/ok']['data']['inferred'][0]['conclusion']=='Mark(x)'
    assert value['cases']['reason/invalid_rule']['error']['code']=='INVALID_INPUT'
    assert value['cases']['ontology/ok']['rdf']['data']
    from scripts.compare_semantic_versions import compare_reports
    assert compare_reports(value,value)['compatible']
