"""Produce genuine native Adapter upgrade evidence from shared technical inputs.

Verification utility only. No Fake factory registration, installs or lock changes.
"""
import argparse,hashlib,json,sys
from importlib.metadata import version
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))  # trusted repository fixtures, never the artifact root
from ontology_platform.infrastructure.backend_factory import create_backend
from ontology_platform.infrastructure.semantica_adapter.backend import REQUESTS,RESULTS
from ontology_platform.infrastructure.semantica_adapter.secure_io import Directory
from ontology_platform.semantic.errors import BackendError
from tests.contract.semantic_cases import OPERATIONS,request,artifact


def generate(workdir:Path)->dict:
    workdir.mkdir(parents=True,exist_ok=False)
    output={'report_version':'0.1.0','backend_kind':'real','backend_version':version('semantica'),'adapter_version':'0.1.0','contract_version':'0.1.0','environment_id':str(Path(sys.prefix).resolve()),'schemas':{op:{'request':REQUESTS[op].model_json_schema(),'result':RESULTS[op].model_json_schema()} for op in OPERATIONS},'cases':{}}
    for operation in OPERATIONS:
        for variant in ('ok','hash_mismatch'):
            capture(workdir,output,operation,variant)
    capture(workdir,output,'reason','invalid_rule')
    capabilities=create_backend('semantica',workdir).capabilities()
    output['capabilities']=[{'operation':item.operation,'supported':item.supported,'limitations':list(item.limitations)} for item in capabilities]
    return output


def capture(workdir,output,operation,variant):
    case_id=operation+'/'+variant
    root=workdir/(operation+'-'+variant); root.mkdir()
    req=request(root,operation)
    if variant=='hash_mismatch': req=req.model_copy(update={'source':req.source.model_copy(update={'sha256':'0'*64})})
    if variant=='invalid_rule':
        req=req.model_copy(update={'rules':artifact(root,'rules.json',json.dumps([{'id':'r1','conditions':['Token(?x)'],'conclusion':'Token(?x)'}]))})
    source=json.loads(req.model_dump_json()); source.pop('run_id')
    row={'operation':operation,'input_sha256':hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    try:
        value=getattr(create_backend('semantica',root),operation)(req)
        row.update(outcome='success',data=value.data,source_refs=list(value.source_refs),object_refs=[json.loads(item.model_dump_json()) for item in value.object_refs])
        row['artifact_hashes']=[{'kind':ref.kind,'sha256':ref.sha256,'size':ref.size} for ref in value.artifact_refs]
        with Directory.root(root) as directory:
            for ref in value.artifact_refs:
                if ref.kind=='tbox':
                    data=directory.read(ref.path,expected_size=ref.size)
                    if hashlib.sha256(data).hexdigest()!=ref.sha256: raise ValueError('Generated RDF digest mismatch')
                    row['rdf']={'format':'nt','data':data.decode()}
    except BackendError as error:
        row.update(outcome='error',error={'code':error.code,'retryable':error.retryable})
    output['cases'][case_id]=row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir',required=True,type=Path); parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    report=generate(args.workdir)
    from scripts.compare_semantic_versions import compare_reports
    if not compare_reports(report,report)['compatible']: raise ValueError('Producer generated invalid report')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps({'backend_kind':report['backend_kind'],'backend_version':report['backend_version'],'environment_id':report['environment_id'],'case_count':len(report['cases'])})); return 0


if __name__=='__main__': raise SystemExit(main())
