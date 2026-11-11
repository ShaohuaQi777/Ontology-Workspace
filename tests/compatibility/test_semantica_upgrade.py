"""Controlled report mutations test the comparer, never fake SDK execution proof."""
from copy import deepcopy
import importlib,json,subprocess,sys
from pathlib import Path
import pytest

OPS=('ingest','parse','extract','build_graph','ontology','validate_shacl','reason')


def report():
    cases={}
    for op in OPS:
        cases[op+'/ok']={'operation':op,'input_sha256':'a'*64,'outcome':'success','data':{'state':'DRAFT'},'source_refs':['source:s1'],'object_refs':[]}
        cases[op+'/hash_mismatch']={'operation':op,'input_sha256':'b'*64,'outcome':'error','error':{'code':'INVALID_INPUT','retryable':False}}
    cases['reason/invalid_rule']={'operation':'reason','input_sha256':'c'*64,'outcome':'error','error':{'code':'INVALID_INPUT','retryable':False}}
    cases['reason/ok']['data']={'asserted':['Token(x)'],'inferred':[{'conclusion':'Mark(x)','state':'DRAFT','confidence':None,'rule_version':'rules:v1:r1','premise_refs':['fact:g1:123']} ]}
    cases['ontology/ok']['rdf']={'format':'nt','data':'_:first <urn:p> "v" .\n'}
    schema={'type':'object','properties':{'run_id':{'type':'string'},'data':{'type':'object'}},'required':['run_id','data']}
    return {'report_version':'0.1.0','backend_kind':'real','backend_version':'0.7.0+ontologyworkspace.4','adapter_version':'0.1.0','contract_version':'0.1.0','environment_id':'env-one','schemas':{op:deepcopy(schema) for op in OPS},'capabilities':[{'operation':op,'supported':True,'limitations':[]} for op in OPS],'cases':cases}


def compare(a,b): return importlib.import_module('scripts.compare_semantic_versions').compare_reports(a,b)


def test_same_report_is_compatible():
    assert compare(report(),report())['compatible']


def test_removed_field_breaks_compatibility():
    a=report(); b=deepcopy(a); del b['schemas']['parse']['properties']['run_id']
    result=compare(a,b); assert not result['compatible'] and result['schema_diffs']


def test_exception_mapping_change_breaks_compatibility():
    a=report(); b=deepcopy(a); b['cases']['parse/hash_mismatch']['error']['code']='BACKEND_FAILURE'
    result=compare(a,b); assert not result['compatible'] and result['error_diffs']


def test_inferred_fact_change_breaks_compatibility():
    a=report(); b=deepcopy(a); b['cases']['reason/ok']['data']['inferred'][0]['conclusion']='Other(x)'
    result=compare(a,b); assert not result['compatible'] and result['semantic_diffs']


def test_rdf_blank_node_labels_do_not_break_compatibility():
    a=report(); b=deepcopy(a); b['cases']['ontology/ok']['rdf']['data']='_:second <urn:p> "v" .\n'
    assert compare(a,b)['compatible']


def test_rdf_literal_change_breaks_compatibility():
    a=report(); b=deepcopy(a); b['cases']['ontology/ok']['rdf']['data']='_:second <urn:p> "other" .\n'
    assert not compare(a,b)['compatible']


def test_missing_required_case_breaks_compatibility():
    a=report(); b=deepcopy(a); del b['cases']['reason/ok']
    assert not compare(a,b)['compatible']


def test_fake_report_not_accepted_as_real_upgrade():
    a=report(); b=deepcopy(a); b['backend_kind']='fake'
    assert not compare(a,b)['compatible']
    b['backend_kind']='real'; b['backend_version']='fake-contract-0.1.0'
    assert not compare(a,b)['compatible']


def test_capability_removal_and_input_change_break_compatibility():
    a=report(); b=deepcopy(a); b['capabilities'][0]['supported']=False
    assert compare(a,b)['capability_diffs']
    b=deepcopy(a); b['cases']['parse/ok']['input_sha256']='d'*64
    assert not compare(a,b)['compatible']


def test_runtime_ids_ignored_but_source_and_rule_provenance_preserved():
    a=report(); b=deepcopy(a); b['environment_id']='env-two'; b['run_id']='different'; b['created_at']='later'
    assert compare(a,b)['compatible']
    b['cases']['reason/ok']['data']['inferred'][0]['premise_refs']=[]
    assert not compare(a,b)['compatible']


def test_extraction_review_contract_not_resampling_values():
    a=report(); a['cases']['extract/ok']['data']={'entities':[{'text':'A','state':'DRAFT','confidence':None}]}
    b=deepcopy(a); b['cases']['extract/ok']['data']['entities'][0]['text']='B'
    assert compare(a,b)['compatible']
    b['cases']['extract/ok']['data']['entities'][0]['state']='CERTIFIED'
    assert not compare(a,b)['compatible']


def test_shacl_random_blank_shape_labels_ignored_but_named_shapes_compared():
    a=report(); a['cases']['validate_shacl/ok']['data']={'conforms':False,'findings':[{'shape':'n'+'a'*32+'b1','constraint':'MinCountConstraintComponent','min_count':2}]}
    b=deepcopy(a); b['cases']['validate_shacl/ok']['data']['findings'][0]['shape']='n'+'b'*32+'b1'
    assert compare(a,b)['compatible']
    b['cases']['validate_shacl/ok']['data']['findings'][0]['min_count']=3
    assert not compare(a,b)['compatible']
    a['cases']['validate_shacl/ok']['data']['findings'][0]['shape']='urn:S1'
    b=deepcopy(a); b['cases']['validate_shacl/ok']['data']['findings'][0]['shape']='urn:S2'
    assert not compare(a,b)['compatible']


def test_invalid_error_and_absent_capability_reports_fail_closed():
    for mutation in ('missing_code','missing_capabilities','non_boolean_capability'):
        a=report()
        if mutation=='missing_code': a['cases']['parse/hash_mismatch']['error']={}
        if mutation=='missing_capabilities': a['capabilities']=[]
        if mutation=='non_boolean_capability': a['capabilities'][0]['supported']=1
        assert not compare(a,deepcopy(a))['compatible']


def test_measured_extraction_score_resampling_does_not_break_contract():
    a=report(); a['cases']['extract/ok']['data']={'entities':[{'text':'A','state':'DRAFT','confidence':0.7}]}
    b=deepcopy(a); b['cases']['extract/ok']['data']['entities'][0]['confidence']=0.8
    assert compare(a,b)['compatible']


def test_rdf_lexical_integer_change_breaks_compatibility():
    a=report(); b=deepcopy(a)
    a['cases']['ontology/ok']['rdf']['data']='_:n <urn:p> "01"^^<http://www.w3.org/2001/XMLSchema#integer> .\n'
    b['cases']['ontology/ok']['rdf']['data']='_:n <urn:p> "1"^^<http://www.w3.org/2001/XMLSchema#integer> .\n'
    assert not compare(a,b)['compatible']


def test_malformed_rdf_fails_closed_without_parser_exception():
    a=report(); b=deepcopy(a); b['cases']['ontology/ok']['rdf']['data']='this is not RDF'
    assert not compare(a,b)['compatible']


def test_cli_returns_failure_for_changed_actual_report_files(tmp_path):
    a=report(); b=deepcopy(a); b['cases']['reason/ok']['data']['inferred']=[]
    left=tmp_path/'baseline.json'; right=tmp_path/'candidate.json'; output=tmp_path/'comparison.json'
    left.write_text(json.dumps(a)); right.write_text(json.dumps(b))
    script=Path(__file__).resolve().parents[2]/'scripts/compare_semantic_versions.py'
    result=subprocess.run([sys.executable,str(script),'--baseline',str(left),'--candidate',str(right),'--output',str(output)],capture_output=True,text=True,timeout=20)
    assert result.returncode==1 and json.loads(output.read_text())['compatible'] is False
