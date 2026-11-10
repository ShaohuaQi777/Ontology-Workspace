"""Tool contracts and genuine filesystem guards; no scenario simulation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from contract_tools.validate import validate_document, validate_pack_paths, verify_release_files


def pack():
    return {'schema_version':'0.1.0','pack_id':'technical-pack','version':'1.0.0','domain':'technical',
            'ontology_entrypoint':'ontology.ttl','sources':[{'id':'s1','kind':'file','path':'source.csv'}]}


def validation():
    return {'schema_version':'0.1.0','run_id':'r1','workspace_revision':'w1','graph_build_id':'g1',
            'backend_version':'0.7.0+ontologyworkspace.3','suite_revision':'q1','status':'passed',
            'findings':[],'evidence':['artifact:report']}


def release():
    return {'schema_version':'0.1.0','release_id':'rel1','version':'1.0.0','workspace_revision':'w1',
            'created_at':'2026-11-10T10:00:00Z','backend_version':'0.7.0+ontologyworkspace.3',
            'artifacts':[{'path':'ontology.ttl','sha256':hashlib.sha256(b'technical').hexdigest(),
                          'size':9,'kind':'tbox','revision':'t1'}], 'validation_run_ids':['r1'], 'approval_id':'a1'}


def operation():
    return {'schema_version':'0.1.0','operation':'extract','status':'succeeded','run_id':'r1',
            'backend_version':'0.7.0+ontologyworkspace.3','source_refs':['source:s1'],
            'artifact_refs':['artifact:a1'],'parameters':{},
            'candidates':[{'id':'c1','kind':'entity','state':'DRAFT','confidence':None}]}


@pytest.mark.parametrize('kind,factory', [('scenario-pack',pack),('validation-result',validation),
                                         ('release-manifest',release),('backend-operation',operation)])
def test_each_schema_has_positive_and_negative_examples(kind,factory):
    assert validate_document(kind,factory()) == []
    errors = validate_document(kind,{})
    assert any(e['code'] == 'SCHEMA_REQUIRED' for e in errors)
    assert all(set(e) == {'pointer','code','message'} for e in errors)


def test_pack_major_version_is_supported():
    value = pack(); value['version'] = '2.0.0'
    assert any(e['code'] == 'PACK_VERSION_UNSUPPORTED' for e in validate_document('scenario-pack',value))


def test_duplicate_source_ids_rejected():
    value = pack(); value['sources'].append(deepcopy(value['sources'][0]))
    assert any(e['code'] == 'DUPLICATE_SOURCE_ID' for e in validate_document('scenario-pack',value))


@pytest.mark.parametrize('path', ['/private/file','../file','x/../../file','C:\\private','a\\b','a/./b'])
def test_absolute_and_parent_paths_rejected(tmp_path,path):
    value = pack(); value['ontology_entrypoint'] = path
    assert any(e['code'] == 'PATH_UNSAFE' for e in validate_pack_paths(tmp_path,value))


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path/'root'; root.mkdir()
    outside = tmp_path/'private'; outside.write_text('technical-only')
    (root/'ontology.ttl').symlink_to(outside)
    assert any(e['code'] == 'PATH_ESCAPE' for e in validate_pack_paths(root,pack()))


def test_missing_pack_entrypoint_rejected(tmp_path):
    assert any(e['code'] == 'PATH_MISSING' for e in validate_pack_paths(tmp_path,pack()))


def test_valid_pack_paths(tmp_path):
    (tmp_path/'ontology.ttl').write_text('technical')
    (tmp_path/'source.csv').write_text('id\nnode')
    assert validate_pack_paths(tmp_path,pack()) == []


def test_duplicate_release_path_rejected(tmp_path):
    (tmp_path/'ontology.ttl').write_bytes(b'technical')
    value = release(); value['artifacts'].append(deepcopy(value['artifacts'][0]))
    assert any(e['code'] == 'DUPLICATE_ARTIFACT_PATH' for e in verify_release_files(tmp_path,value))


def test_bad_hash_rejected(tmp_path):
    (tmp_path/'ontology.ttl').write_bytes(b'technical')
    value = release(); value['artifacts'][0]['sha256'] = '0'*64
    assert any(e['code'] == 'HASH_MISMATCH' for e in verify_release_files(tmp_path,value))


def test_release_size_mismatch_rejected(tmp_path):
    (tmp_path/'ontology.ttl').write_bytes(b'technical')
    value = release(); value['artifacts'][0]['size'] = 1
    assert any(e['code'] == 'SIZE_MISMATCH' for e in verify_release_files(tmp_path,value))


def test_valid_release_files(tmp_path):
    (tmp_path/'ontology.ttl').write_bytes(b'technical')
    assert verify_release_files(tmp_path,release()) == []


def test_inferred_finding_requires_rule_and_premises():
    value = validation(); value['status'] = 'failed'
    value['findings'] = [{'severity':'error','code':'TECHNICAL_FINDING','resource':'urn:n',
                          'message':'Constraint failed','source_refs':['source:s1'],'inferred':True}]
    assert validate_document('validation-result',value)
    value['findings'][0].update(rule_version='rule:v1',premise_refs=['fact:f1'])
    assert validate_document('validation-result',value) == []


def test_backend_error_is_platform_dto():
    value = operation(); value['status'] = 'failed'
    value['error'] = {'code':'BACKEND_FAILURE','message':'Backend operation failed', 'run_id':'r1','retryable':False}
    value.pop('candidates')
    assert validate_document('backend-operation',value) == []
    value['error']['traceback'] = 'native stack'
    assert validate_document('backend-operation',value)


def test_generated_candidate_is_draft():
    value = operation(); value['candidates'][0]['state'] = 'CERTIFIED'
    assert validate_document('backend-operation',value)


def test_null_confidence_is_not_perfect_score():
    value = operation()
    assert validate_document('backend-operation',value) == []
    assert value['candidates'][0]['confidence'] is None
    value['candidates'][0]['confidence'] = 1.1
    assert validate_document('backend-operation',value)


def test_secret_reference_never_contains_plaintext():
    value = pack(); value['sources'][0]['credential_ref'] = 'cred:local:s1'
    assert validate_document('scenario-pack',value) == []
    value['sources'][0]['password'] = 'technical-test-secret'
    assert validate_document('scenario-pack',value)
    value['sources'][0].pop('password'); value['sources'][0]['credential_ref'] = {'password':'technical-test-secret'}
    assert validate_document('scenario-pack',value)


def test_failed_or_unavailable_cannot_claim_pass():
    value = operation(); value['error'] = {'code':'BACKEND_FAILURE','message':'Backend failed','run_id':'r1','retryable':False}
    assert validate_document('backend-operation',value)


def test_contract_cli_real_exit_states(tmp_path):
    path = tmp_path/'contract.json'; path.write_text(json.dumps(pack()))
    result = subprocess.run([sys.executable,'-m','contract_tools.validate','--kind','scenario-pack','--file',str(path)],capture_output=True)
    assert result.returncode == 0
    path.write_text('{}')
    result = subprocess.run([sys.executable,'-m','contract_tools.validate','--kind','scenario-pack','--file',str(path)],capture_output=True)
    assert result.returncode == 1
