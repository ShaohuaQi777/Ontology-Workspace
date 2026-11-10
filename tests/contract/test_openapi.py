"""OpenAPI refs and actual request/response contract instances, not YAML-only."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
import yaml
from contract_tools.validate import validate_document

OPS = {'ingest':['source_id'],'parse':['source_id'],'extract':['source_id'],'normalize':['source_id'],
       'align':['source_id','schema_id'],'build_graph':['graph_id'],'import_ontology':['source_id'],
       'edit_ontology':['schema_id'],'generate_ontology':['graph_id'],'validate':['graph_id','suite_id'],
       'reason':['graph_id','ruleset_id'],'detect_conflicts':['graph_id'],'export':['release_id'],'capabilities':[]}


def test_openapi_all_refs_and_operations():
    document = yaml.safe_load(Path('contracts/semantic-backend.openapi.yaml').read_text())
    assert document['openapi'] == '3.1.0'
    actual = {entry['operationId'] for path in document['paths'].values() for entry in path.values()}
    assert actual == set(OPS)
    pending = [document]
    while pending:
        item = pending.pop()
        if isinstance(item,dict):
            if '$ref' in item:
                ref = item['$ref']
                if ref.startswith('#/'):
                    target = document
                    for component in ref[2:].split('/'):
                        target = target[component]
                else:
                    name,fragment = ref.split('#',1)
                    target = json.loads((Path('contracts') / name).read_text())
                    for component in fragment.lstrip('/').split('/'):
                        target = target[component]
                assert isinstance(target,dict)
            pending.extend(item.values())
        elif isinstance(item,list):
            pending.extend(item)


@pytest.mark.parametrize('op,ids',OPS.items())
def test_each_operation_request_response_and_negative_instance(op,ids):
    request = {'schema_version':'0.1.0','operation':op,'run_id':'r1','source_refs':['source:s1'],
               'parameters':{},'inputs':{key:'technical-id' for key in ids}}
    assert validate_document('backend-operation',request) == []
    invalid = deepcopy(request)
    if ids:
        invalid['inputs'].pop(ids[0])
    else:
        invalid.pop('run_id')
    assert validate_document('backend-operation',invalid)
    response = {'schema_version':'0.1.0','operation':op,'run_id':'r1','source_refs':['source:s1'],
                'parameters':{},'status':'succeeded','backend_version':'0.7.0+ontologyworkspace.3','artifact_refs':['artifact:a1']}
    assert validate_document('backend-operation',response) == []
    response.pop('backend_version')
    assert validate_document('backend-operation',response)
