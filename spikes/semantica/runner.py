"""Run native probes and persist only bounded evidence, without exception text."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from scripts.verify_a0 import REQUIRED_CASES, evaluate_gate
from .cases import CASES, NativeAPIUnavailable
from .models import ProbeEvidence, installed_backend_version, safe_parameters
from .runtime import quiet_native_runtime


def run_case(case_id: str, output_dir: Path) -> ProbeEvidence:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run_id = f'run-{uuid.uuid4().hex}'
    known = case_id in CASES
    safe_case_id = case_id if known else 'unsupported_case'
    base = {'case_id': safe_case_id, 'backend_version': installed_backend_version(), 'run_id': run_id}
    if not known:
        evidence = ProbeEvidence(**base, status='unavailable', error_code='UNSUPPORTED_CASE')
    elif base['backend_version'] is None:
        evidence = ProbeEvidence(**base, status='unavailable', error_code='DEPENDENCY_UNAVAILABLE')
    else:
        work = root / run_id
        work.mkdir(mode=0o700)
        try:
            with quiet_native_runtime(work):
                result = CASES[case_id](work)
            checks = result.get('checks', {})
            hashes = {}
            for label, artifact in result.get('artifacts', {}).items():
                path = Path(artifact).resolve(strict=True)
                if not path.is_relative_to(work) or not path.is_file():
                    raise ValueError('Artifact must be inside this run')
                hashes[label] = hashlib.sha256(path.read_bytes()).hexdigest()
            passed = bool(checks) and all(value is True for value in checks.values())
            evidence = ProbeEvidence(**base, status='passed' if passed else 'failed',
                api_symbol=result.get('api_symbol', ''), source_refs=result.get('source_refs', []),
                parameters=safe_parameters(result.get('parameters', {})), artifact_hashes=hashes,
                checks=checks, error_code=None if passed else 'CHECK_FAILED')
        except NativeAPIUnavailable:
            evidence = ProbeEvidence(**base, status='unavailable', error_code='NATIVE_API_UNAVAILABLE')
        except ImportError:
            evidence = ProbeEvidence(**base, status='unavailable', error_code='DEPENDENCY_UNAVAILABLE')
        except NotImplementedError:
            evidence = ProbeEvidence(**base, status='unavailable', error_code='CASE_NOT_IMPLEMENTED')
        except Exception:
            evidence = ProbeEvidence(**base, status='failed', error_code='BACKEND_FAILURE')
    path = root / f'{safe_case_id}-{run_id}.json'
    with path.open('x', encoding='utf-8') as handle:
        handle.write(evidence.model_dump_json(indent=2))
    return evidence


def run_all(output_dir: Path) -> list[ProbeEvidence]:
    return [run_case(case_id, output_dir) for case_id in REQUIRED_CASES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = run_all(args.output)
    gate = evaluate_gate(evidence)
    summary = {'evidence': [item.model_dump(mode='json') for item in evidence], 'gate': gate}
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if gate['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
