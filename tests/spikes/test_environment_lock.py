"""REAL runtime/lock comparison, never a mock metadata fixture."""
import importlib.metadata
import json
from pathlib import Path
import sys
import tomllib
from packaging.requirements import Requirement


def test_runtime_matches_dependency_lock():
    lock = tomllib.loads(Path('uv.lock').read_text())
    project = tomllib.loads(Path('pyproject.toml').read_text())
    versions = {package['name']: package['version'] for package in lock['package']}
    expected = json.loads(Path('patches/semantica/manifest.json').read_text())['version']
    assert sys.version_info[:2] == (3, 12)
    assert versions['semantica'] == importlib.metadata.version('semantica') == expected
    dependencies = project['project']['dependencies'] + project['dependency-groups']['dev']
    for spec in dependencies:
        name = Requirement(spec).name.lower().replace('_', '-')
        assert importlib.metadata.version(name) == versions[name]


def test_lock_has_small_official_model_not_large_model_stack():
    lock = tomllib.loads(Path('uv.lock').read_text())
    names = {package['name'] for package in lock['package']}
    assert {'spacy', 'en-core-web-sm', 'pyoxigraph', 'sqlalchemy'} <= names
    assert not {'torch', 'transformers', 'tensorflow', 'docling'} & names
