"""Fixtures for error-path UNIT tests only. Native tests must not use this fixture."""
import importlib.metadata
import pytest


@pytest.fixture
def backend_metadata(monkeypatch):
    original_version = importlib.metadata.version

    def unit_metadata(name):
        if name == 'semantica':
            return '0.7.0'
        return original_version(name)

    monkeypatch.setattr(importlib.metadata, 'version', unit_metadata)
