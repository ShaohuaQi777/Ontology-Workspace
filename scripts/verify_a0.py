"""Fail-closed native evidence gate. Unit gate success is not system acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding='utf-8'))
        evidence = data.get('evidence') if isinstance(data, dict) else data
        result = evaluate_gate(evidence)
    except (OSError, UnicodeError, ValueError, TypeError):
        result = {'passed': False, 'error_code': 'INVALID_EVIDENCE'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
