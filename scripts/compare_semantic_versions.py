"""Conservative real-report upgrade gate; never installs or changes a lock."""
import argparse,json,re
from pathlib import Path
from rdflib import Graph,BNode
from rdflib.compare import isomorphic
from rdflib.exceptions import ParserError

OPS=('ingest','parse','extract','build_graph','ontology','validate_shacl','reason')
REQUIRED={op+'/'+case for op in OPS for case in ('ok','hash_mismatch')}|{'reason/invalid_rule'}
LIMIT=4194304


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def schema_view(value):
    if isinstance(value,dict): return {k:schema_view(v) for k,v in value.items() if k not in ('title','description','$comment')}
    if isinstance(value,list): return [schema_view(v) for v in value]
    return value


def shape(value):
    if isinstance(value,dict): return {k:shape(v) for k,v in value.items()}
    if isinstance(value,list): return sorted({canonical(shape(v)) for v in value})
    return type(value).__name__


def semantics(operation,data):
    if operation=='extract':
        # Candidate content/count may vary on resampling. Field types and review
        # state/confidence are contracts; do not compare generated prose values.
        def review(value):
            if isinstance(value,dict): return {k:(v if k=='state' else review(v)) for k,v in value.items()}
            if isinstance(value,list): return sorted({canonical(review(v)) for v in value})
            return type(value).__name__
        return {'shape':shape(data),'review':review(data)}
    if operation=='validate_shacl':
        def clean(value):
            if isinstance(value,dict):
                return {k:('_:anonymous-shape' if k in ('shape','source_shape','sourceShape') and isinstance(v,str) and re.fullmatch(r'(?:_:)?n[0-9a-f]{32}b[0-9]+',v) else clean(v)) for k,v in value.items()}
            if isinstance(value,list): return sorted((clean(v) for v in value),key=canonical)
            return value
        return clean(data)
    if operation=='build_graph':
        return {k:sorted(v,key=canonical) if isinstance(v,list) else v for k,v in data.items()}
    return data


def valid_report(report):
    if not isinstance(report,dict) or report.get('backend_kind')!='real': return False
    version=report.get('backend_version')
    if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[.+-][a-zA-Z0-9.-]+)?',version) or 'fake' in version.lower(): return False
    if any(not isinstance(report.get(k),str) or not report[k] for k in ('report_version','adapter_version','contract_version')): return False
    if not isinstance(report.get('schemas'),dict) or not all(op in report['schemas'] for op in OPS): return False
    cases=report.get('cases')
    if not isinstance(cases,dict) or not REQUIRED.issubset(cases) or len(cases)>64: return False
    for case in cases.values():
        if not isinstance(case,dict) or case.get('operation') not in OPS or not re.fullmatch('[0-9a-f]{64}',str(case.get('input_sha256',''))): return False
        if case.get('outcome') not in ('success','error'): return False
        if case['outcome']=='success' and not isinstance(case.get('data'),dict): return False
        if case['outcome']=='error':
            error=case.get('error')
            if not isinstance(error,dict) or error.get('code') not in ('INVALID_INPUT','UNSUPPORTED_CAPABILITY','BACKEND_FAILURE','TIMEOUT','CONTRACT_VIOLATION') or type(error.get('retryable')) is not bool: return False
    caps=report.get('capabilities')
    if not isinstance(caps,list) or len(caps)!=len(OPS): return False
    if any(not isinstance(cap,dict) or type(cap.get('supported')) is not bool or not isinstance(cap.get('limitations'),list) for cap in caps): return False
    return {cap.get('operation') for cap in caps}==set(OPS)


def rdf_equal(left,right):
    if not isinstance(left,dict) or not isinstance(right,dict) or left.get('format')!='nt' or right.get('format')!='nt': return False
    graphs=[]
    for value in (left,right):
        data=value.get('data')
        if not isinstance(data,str) or len(data.encode())>1048576: return False
        graph=Graph().parse(data=data,format='nt')
        if len(graph)>128 or len({term for triple in graph for term in triple if isinstance(term,BNode)})>32: return False
        graphs.append(graph)
    return isomorphic(*graphs)


def compare_reports(baseline:dict,candidate:dict)->dict:
    result={name:[] for name in ('schema_diffs','capability_diffs','semantic_diffs','error_diffs')}
    try:
        if len(canonical(baseline).encode())>LIMIT or len(canonical(candidate).encode())>LIMIT or not valid_report(baseline) or not valid_report(candidate):
            result['schema_diffs'].append('Invalid/non-real report or missing required cases')
        else:
            for key in ('report_version','adapter_version','contract_version'):
                if baseline[key]!=candidate[key]: result['schema_diffs'].append(key)
            if schema_view(baseline['schemas'])!=schema_view(candidate['schemas']): result['schema_diffs'].append('Request/result schema changed')
            capabilities={x.get('operation'):x for x in candidate['capabilities'] if isinstance(x,dict)}
            for cap in baseline['capabilities']:
                other=capabilities.get(cap.get('operation')) if isinstance(cap,dict) else None
                if other is None or any(cap.get(k)!=other.get(k) for k in ('supported','limitations')):
                    result['capability_diffs'].append(str(cap))
            for case_id,left in baseline['cases'].items():
                right=candidate['cases'].get(case_id)
                if right is None or left['input_sha256']!=right['input_sha256'] or left['operation']!=right['operation']:
                    result['semantic_diffs'].append(case_id+': input/case changed'); continue
                if left['outcome']!=right['outcome']:
                    result['error_diffs'].append(case_id+': outcome changed'); continue
                if left['outcome']=='error':
                    if left['error']!=right['error']: result['error_diffs'].append(case_id)
                    continue
                if any(left.get(k)!=right.get(k) for k in ('source_refs','object_refs')): result['semantic_diffs'].append(case_id+': provenance')
                if semantics(left['operation'],left['data'])!=semantics(right['operation'],right['data']): result['semantic_diffs'].append(case_id+': semantic/review data')
                if ('rdf' in left or 'rdf' in right) and not rdf_equal(left.get('rdf'),right.get('rdf')): result['semantic_diffs'].append(case_id+': RDF graph')
    except (ValueError,TypeError,KeyError,RecursionError,ParserError):
        result['schema_diffs'].append('Malformed or unbounded report')
    result['compatible']=not any(result.values())
    return result


def load(path):
    with Path(path).open('rb') as stream: data=stream.read(LIMIT+1)
    if len(data)>LIMIT: raise ValueError('Report exceeds budget')
    return json.loads(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True,type=Path); parser.add_argument('--candidate',required=True,type=Path); parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try: result=compare_reports(load(args.baseline),load(args.candidate))
    except (ValueError,OSError): result={'compatible':False,'schema_diffs':['Cannot read valid bounded reports'],'capability_diffs':[],'semantic_diffs':[],'error_diffs':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2)); return 0 if result['compatible'] else 1


if __name__=='__main__': raise SystemExit(main())
