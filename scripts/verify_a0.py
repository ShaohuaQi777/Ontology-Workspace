"""Fail-closed native evidence gate. Unit gate success is not system acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

REQUIRED_CASES = (
    'ingest_csv', 'ingest_json', 'ingest_sqlite', 'parse_pdf', 'parse_docx',
    'extract_entities_relations_events', 'build_graph', 'ontology_generate',
    'ontology_roundtrip', 'ontology_edit', 'shacl_pass', 'shacl_fail',
    'reason_forward', 'conflict_evidence', 'provenance_export',
    'query_select_ask', 'normalize_align',
)
VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)$')


def evaluate_gate(evidence: list[Any]) -> dict[str, Any]:
    if not isinstance(evidence, list):
        return {'passed': False, 'error_code': 'INVALID_EVIDENCE',
                'missing_cases': list(REQUIRED_CASES)}
    entries = []
    invalid_entries = 0
    for item in evidence:
        if hasattr(item, 'model_dump'):
            item = item.model_dump(mode='json')
        if not isinstance(item, dict) or not isinstance(item.get('case_id'), str):
            invalid_entries += 1
        else:
            entries.append(item)
    counts = Counter(item['case_id'] for item in entries)
    missing = [case for case in REQUIRED_CASES if counts[case] == 0]
    duplicates = [case for case in REQUIRED_CASES if counts[case] > 1]
    unexpected_count = sum(count for case, count in counts.items() if case not in REQUIRED_CASES)
    versions = set()
    failed = []
    for item in entries:
        case = item['case_id']
        if case not in REQUIRED_CASES:
            continue
        version = item.get('backend_version')
        valid_version = isinstance(version, str) and bool(VERSION_PATTERN.fullmatch(version))
        if valid_version:
            versions.add(version)
        checks = item.get('checks')
        valid_checks = isinstance(checks, dict) and bool(checks) and all(v is True for v in checks.values())
        sources = item.get('source_refs')
        valid_sources = isinstance(sources, list) and bool(sources) and all(isinstance(s, str) and bool(s) for s in sources)
        symbol = item.get('api_symbol')
        valid_symbol = isinstance(symbol, str) and symbol.startswith('semantica.')
        if not (item.get('status') == 'passed' and item.get('error_code') is None
                and valid_version and valid_checks and valid_sources and valid_symbol):
            failed.append(case)
    passed = not (missing or duplicates or failed or invalid_entries or unexpected_count) and len(versions) == 1
    return {
        'passed': passed,
        'missing_cases': missing,
        'duplicate_cases': duplicates,
        'failed_cases': sorted(set(failed)),
        'invalid_entry_count': invalid_entries,
        'unexpected_case_count': unexpected_count,
        'backend_versions': sorted(versions),
        'required_case_count': len(REQUIRED_CASES),
        'scope': 'native_probe_evidence_only',
        'not_yet_verified': ['locked_clean_install', 'shared_contracts', 'adapter_isolation', 'upgrade_compatibility'],
    }


def evaluate_contract_gate(evidence: list[Any], contract_exit_code: int) -> dict[str, Any]:
    result = evaluate_gate(evidence)
    result['contract_exit_code'] = contract_exit_code
    result['passed'] = result['passed'] and type(contract_exit_code) is int and contract_exit_code == 0
    result['scope'] = 'native_and_contract_evidence_only'
    return result


def evaluate_p0_gate(evidence: list[Any], verification: dict) -> dict[str, Any]:
    result=evaluate_gate(evidence)
    keys=('contract_exit_code','clean_install_exit_code','baseline_report_exit_code','candidate_report_exit_code')
    codes=all(type(verification.get(k)) is int and verification[k]==0 for k in keys)
    baseline=verification.get('baseline_environment'); candidate=verification.get('candidate_environment')
    isolated=isinstance(baseline,str) and isinstance(candidate,str) and bool(baseline) and bool(candidate) and baseline!=candidate
    comparison=verification.get('comparison')
    compatible=isinstance(comparison,dict) and comparison.get('compatible') is True
    version_matches=result.get('backend_versions')==[verification.get('backend_version')]
    native_passed=result['passed']
    result.update(verification)
    result['passed']=native_passed and codes and isolated and compatible and version_matches
    result['scope']='g_p0_execution_only'
    result['release_approved']=False
    result['not_yet_verified']=['independent_security_review','product_delivery','linux_deployment']
    return result


def verify_p0_execution(evidence):
    import os,shutil
    from uuid import uuid4
    from importlib.metadata import version
    root=Path(__file__).resolve().parents[1]
    if str(root) not in sys.path: sys.path.insert(0,str(root))
    from scripts.compare_semantic_versions import load,compare_reports
    work=root/'.runtime'/('gp0-'+uuid4().hex)
    work.mkdir(parents=True,mode=0o700)
    def run(command,env=None):
        try:
            return subprocess.run(command,cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=240).returncode
        except (OSError,subprocess.TimeoutExpired): return 124
    verification={'backend_version':version('semantica')}
    # Gate tests live outside these folders, avoiding recursive gate execution.
    verification['contract_exit_code']=run([sys.executable,'-m','pytest','tests/contract','tests/compatibility','tests/native_document','tests/spikes','-q'])
    script=str(root/'scripts/record_semantic_contract.py')
    baseline=work/'baseline.json'; candidate=work/'candidate.json'
    verification['baseline_report_exit_code']=run([sys.executable,script,'--workdir',str(work/'baseline-cases'),'--output',str(baseline)])
    uv=shutil.which('uv')
    env=dict(os.environ,UV_CACHE_DIR=str(root/'.cache/uv'),UV_PROJECT_ENVIRONMENT=str(work/'environment'))
    verification['clean_install_exit_code']=run([uv,'sync','--locked','--offline','--python','python3.12'],env) if uv else 127
    verification['candidate_report_exit_code']=run([uv,'run','--locked','--offline','python',script,'--workdir',str(work/'candidate-cases'),'--output',str(candidate)],env) if uv and verification['clean_install_exit_code']==0 else 127
    if verification['baseline_report_exit_code']==0 and verification['candidate_report_exit_code']==0:
        left=load(baseline); right=load(candidate)
        verification.update(baseline_environment=left['environment_id'],candidate_environment=right['environment_id'],comparison=compare_reports(left,right))
    verification['evidence_directory']=str(work.relative_to(root))
    (work/'execution.json').write_text(json.dumps(verification,indent=2)+'\n')
    return evaluate_p0_gate(evidence,verification)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--verify-contracts', action='store_true', help='Run the actual local contract suite, not a caller-provided verdict')
    parser.add_argument('--verify-p0',action='store_true',help='Execute real shared contracts, fresh locked offline install and current-version comparison; not review approval')
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding='utf-8'))
        evidence = data.get('evidence') if isinstance(data, dict) else data
        result = evaluate_gate(evidence)
        if args.verify_contracts:
            try:
                completed = subprocess.run([sys.executable, '-m', 'pytest', 'tests/contract', '-q'],
                                           cwd=Path(__file__).resolve().parents[1],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
                contract_code = completed.returncode
            except (OSError, subprocess.TimeoutExpired):
                contract_code = 124
            result = evaluate_contract_gate(evidence, contract_code)
        if args.verify_p0:
            result=verify_p0_execution(evidence)
    except (OSError, UnicodeError, ValueError, TypeError):
        result = {'passed': False, 'error_code': 'INVALID_EVIDENCE'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
