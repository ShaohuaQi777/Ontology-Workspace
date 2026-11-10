"""Stdlib contract tests for exception isolation; no native support claims."""
import json
from pathlib import Path
import sys
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from ontology_platform.semantic.errors import BackendError, invoke_guarded


class ErrorBoundaryTests(unittest.TestCase):
    def test_native_exceptions_are_wrapped(self):
        def native():
            raise RuntimeError('native detail must not cross the boundary')
        with self.assertRaises(BackendError) as raised:
            invoke_guarded(native, run_id='run-test')
        self.assertEqual(raised.exception.code, 'BACKEND_FAILURE')

    def test_secret_is_absent_from_error_and_traceback(self):
        secret = 'synthetic-unit-secret'
        def native():
            raise RuntimeError(secret)
        try:
            invoke_guarded(native, run_id='run-test')
        except BackendError as error:
            rendered = ''.join(traceback.format_exception(error))
            self.assertNotIn(secret, rendered)
            self.assertNotIn(secret, json.dumps(error.to_dict()))
            self.assertIsNone(error.__cause__)
            self.assertIsNone(error.__context__)
        else:
            self.fail('Native failure must not be replaced with success')

    def test_dependency_failure_has_stable_code(self):
        def native():
            raise ImportError('some upstream optional module')
        with self.assertRaises(BackendError) as raised:
            invoke_guarded(native, run_id='run-test')
        self.assertEqual(raised.exception.code, 'DEPENDENCY_UNAVAILABLE')
        self.assertFalse(raised.exception.retryable)

    def test_timeout_is_retryable(self):
        def native():
            raise TimeoutError('connection URI contains native details')
        with self.assertRaises(BackendError) as raised:
            invoke_guarded(native, run_id='run-test')
        self.assertEqual(raised.exception.code, 'TIMEOUT')
        self.assertTrue(raised.exception.retryable)

    def test_invalid_input_has_no_native_arguments(self):
        native_object = object()
        def native():
            raise ValueError(native_object)
        with self.assertRaises(BackendError) as raised:
            invoke_guarded(native, run_id='run-test')
        error = raised.exception
        self.assertEqual(error.code, 'INVALID_INPUT')
        self.assertNotIn(native_object, error.args)
        self.assertEqual(set(error.to_dict()), {'code', 'message', 'run_id', 'retryable'})

    def test_valid_result_is_preserved_and_called_once(self):
        calls = []
        def native():
            calls.append(True)
            return {'result': 'technical-value'}
        self.assertEqual(invoke_guarded(native, run_id='run-test'), {'result': 'technical-value'})
        self.assertEqual(calls, [True])

    def test_existing_platform_error_preserves_code(self):
        def native():
            raise BackendError('UNSUPPORTED_CAPABILITY', 'Unsupported operation', 'run-test', False)
        with self.assertRaises(BackendError) as raised:
            invoke_guarded(native, run_id='run-test')
        self.assertEqual(raised.exception.code, 'UNSUPPORTED_CAPABILITY')

    def test_unknown_error_code_rejected(self):
        with self.assertRaises(ValueError):
            BackendError('unknown', 'Message', 'run-test', False)

    def test_error_values_must_be_platform_scalars(self):
        with self.assertRaises(ValueError):
            BackendError('BACKEND_FAILURE', object(), 'run-test', False)
        with self.assertRaises(ValueError):
            BackendError('BACKEND_FAILURE', 'Message', object(), False)

    def test_error_run_id_is_bounded(self):
        with self.assertRaises(ValueError):
            BackendError('BACKEND_FAILURE', 'Message', 'x' * 1024, False)

    def test_invalid_run_context_never_calls_native(self):
        calls = []
        with self.assertRaises(ValueError):
            invoke_guarded(lambda: calls.append(True), run_id='bad id\n')
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
