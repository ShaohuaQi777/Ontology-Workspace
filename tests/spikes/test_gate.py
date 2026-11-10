"""Gate logic tests use synthetic evidence, never proof of native support."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.verify_a0 import evaluate_gate, REQUIRED_CASES


def valid_report():
    return [dict(case_id=name, status='passed', backend_version='0.7.0',
                 api_symbol='semantica.test_symbol', source_refs=['urn:test:source'],
                 checks={'expected_result': True}, error_code=None)
            for name in REQUIRED_CASES]


class GateTests(unittest.TestCase):
    def test_missing_case_fails_gate(self):
        result = evaluate_gate([])
        self.assertFalse(result['passed'])
        self.assertIn('build_graph', result['missing_cases'])

    def test_unavailable_fails_gate(self):
        report = valid_report()
        report[0]['status'] = 'unavailable'
        report[0]['error_code'] = 'DEPENDENCY_UNAVAILABLE'
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_duplicate_case_fails_gate(self):
        report = valid_report()
        report.append(report[0].copy())
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_mixed_backend_versions_fail_gate(self):
        report = valid_report()
        report[0]['backend_version'] = 'unverified-candidate'
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_all_required_cases_pass(self):
        self.assertTrue(evaluate_gate(valid_report())['passed'])

    def test_missing_checks_fail_gate(self):
        report = valid_report()
        report[0]['checks'] = {}
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_failed_check_fails_gate(self):
        report = valid_report()
        report[0]['checks']['expected_result'] = False
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_fake_backend_is_not_native_evidence(self):
        report = valid_report()
        for entry in report:
            entry['backend_version'] = 'fake'
            entry['api_symbol'] = 'fake.backend'
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_missing_version_fails_gate(self):
        report = valid_report()
        for entry in report:
            entry['backend_version'] = None
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_missing_source_fails_gate(self):
        report = valid_report()
        report[0]['source_refs'] = []
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_passed_status_with_error_fails_gate(self):
        report = valid_report()
        report[0]['error_code'] = 'BACKEND_FAILURE'
        self.assertFalse(evaluate_gate(report)['passed'])

    def test_gate_cannot_accept_empty_report_from_cli(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'summary.json'
            path.write_text('[]')
            result = subprocess.run([sys.executable, str(root / 'scripts/verify_a0.py'),
                                     '--evidence', str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('"passed": false', result.stdout)


if __name__ == '__main__':
    unittest.main()
