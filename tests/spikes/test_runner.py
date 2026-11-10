"""Unit-only error branch tests; real backend successes have separate tests."""
import importlib.metadata
import json
from pathlib import Path
import pytest
from spikes.semantica import runner

# Explicit unit-only metadata fixture, never used in native capability tests.
pytestmark = pytest.mark.usefixtures('backend_metadata')


def test_missing_dependency_records_unavailable(monkeypatch, tmp_path):
    def unavailable(directory):
        raise ImportError('optional parser is missing')
    monkeypatch.setitem(runner.CASES, 'parse_pdf', unavailable)
    evidence = runner.run_case('parse_pdf', tmp_path)
    assert evidence.status == 'unavailable'
    assert evidence.error_code == 'DEPENDENCY_UNAVAILABLE'
    assert evidence.backend_version == importlib.metadata.version('semantica')


def test_runtime_failure_records_failed(monkeypatch, tmp_path):
    def broken(directory):
        raise RuntimeError('native implementation failed')
    monkeypatch.setitem(runner.CASES, 'build_graph', broken)
    evidence = runner.run_case('build_graph', tmp_path)
    assert evidence.status == 'failed'
    assert evidence.error_code == 'BACKEND_FAILURE'


def test_exception_does_not_leak_secret(monkeypatch, tmp_path):
    secret = 'synthetic-secret-for-unit-test-only'
    def broken(directory):
        raise RuntimeError(f'password={secret}, endpoint=https://host.invalid/?token={secret}')
    monkeypatch.setitem(runner.CASES, 'parse_pdf', broken)
    evidence = runner.run_case('parse_pdf', tmp_path)
    assert secret not in evidence.model_dump_json()
    files = list(tmp_path.glob('*.json'))
    assert files
    assert all(secret not in path.read_text() for path in files)


def test_no_fallback_when_semantica_fails(monkeypatch, tmp_path):
    calls = []
    def broken(directory):
        calls.append(directory)
        raise RuntimeError('do not replace this with fake success')
    monkeypatch.setitem(runner.CASES, 'build_graph', broken)
    evidence = runner.run_case('build_graph', tmp_path)
    assert len(calls) == 1
    assert evidence.status == 'failed'
    assert not evidence.artifact_hashes


def test_unknown_case_is_rejected_without_path_escape(tmp_path):
    evidence = runner.run_case('../escape', tmp_path)
    assert evidence.status == 'unavailable'
    assert evidence.error_code == 'UNSUPPORTED_CASE'
    assert all(path.parent == tmp_path for path in tmp_path.glob('*.json'))


def test_failed_native_check_is_not_passed(monkeypatch, tmp_path):
    def invalid(directory):
        return {'api_symbol': 'semantica.example', 'source_refs': ['urn:technical:source'],
                'checks': {'expected_result': False}}
    monkeypatch.setitem(runner.CASES, 'build_graph', invalid)
    evidence = runner.run_case('build_graph', tmp_path)
    assert evidence.status == 'failed'
    assert evidence.error_code == 'CHECK_FAILED'


def test_sensitive_parameters_are_not_written(monkeypatch, tmp_path):
    def valid(directory):
        return {'api_symbol': 'semantica.example', 'source_refs': ['urn:technical:source'],
                'checks': {'expected_result': True},
                'parameters': {'format': 'turtle', 'password': 'synthetic-password',
                               'endpoint': 'https://host.invalid/?token=synthetic-token'}}
    monkeypatch.setitem(runner.CASES, 'build_graph', valid)
    evidence = runner.run_case('build_graph', tmp_path)
    assert evidence.parameters == {'format': 'turtle'}
    assert 'synthetic-password' not in evidence.model_dump_json()
    assert 'synthetic-token' not in evidence.model_dump_json()


def test_native_logging_and_stdio_do_not_leak(monkeypatch, tmp_path, capsys):
    import logging
    import sys
    root = logging.getLogger('semantica')
    previous = root.handlers[:]
    handler = logging.StreamHandler(sys.stdout)
    root.handlers = [handler]
    secret = 'synthetic-native-log-secret'
    def native(directory):
        from semantica.utils.logging import get_logger
        get_logger('probe_secret').error(secret)
        print(secret)
        raise RuntimeError(secret)
    monkeypatch.setitem(runner.CASES, 'parse_pdf', native)
    try:
        evidence = runner.run_case('parse_pdf', tmp_path)
        output = capsys.readouterr()
        assert secret not in output.out + output.err
        assert secret not in evidence.model_dump_json()
    finally:
        root.handlers = previous
        handler.close()


def test_safe_runtime_settings_before_case(monkeypatch, tmp_path):
    import os
    def native(directory):
        return {'api_symbol': 'semantica.example', 'source_refs': ['urn:technical:source'],
                'checks': {'memory_cache': os.environ.get('SEMANTICA_CACHE_BACKEND') == 'memory',
                           'offline_hub': os.environ.get('HF_HUB_OFFLINE') == '1',
                           'offline_transformers': os.environ.get('TRANSFORMERS_OFFLINE') == '1'}}
    monkeypatch.setitem(runner.CASES, 'build_graph', native)
    assert runner.run_case('build_graph', tmp_path).status == 'passed'
