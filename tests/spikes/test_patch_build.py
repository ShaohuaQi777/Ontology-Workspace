"""Build artifact correctness; not proof of semantic capability."""
import base64
import csv
import hashlib
import io
from pathlib import Path
import shutil
from zipfile import ZipFile
import pytest
from scripts.build_semantica_patch import build_patch

import json
VERSION = json.loads(Path('patches/semantica/manifest.json').read_text())['version']


@pytest.fixture(scope='module')
def base_dir(tmp_path_factory):
    wheel = Path('vendor/upstream/semantica-0.7.0-py3-none-any.whl')
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == 'faf27d6259ae813ddb44c5213e2f8867592f27e6e3d6b47cea10f1844513799f'
    base = tmp_path_factory.mktemp('verified-semantic-base')
    with ZipFile(wheel) as archive:
        for name in archive.namelist():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
        archive.extractall(base)
    return base


def test_patch_wheel_version_record_and_module(tmp_path, base_dir):
    wheel = build_patch(base_dir, tmp_path)
    bundled = Path(f'vendor/wheels/semantica-{VERSION}-py3-none-any.whl')
    assert wheel.read_bytes() == bundled.read_bytes()
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        assert 'semantica/ontology/document.py' in names
        assert 'semantica/parse/bounded_pdf.py' in names
        assert f'__version__ = "{VERSION}"' in archive.read('semantica/__init__.py').decode()
        assert f'Version: {VERSION}\n' in archive.read(f'semantica-{VERSION}.dist-info/METADATA').decode()
        assert any(name.endswith('licenses/LICENSE') for name in names)
        record = f'semantica-{VERSION}.dist-info/RECORD'
        rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
        assert {row[0] for row in rows} == set(names)
        for name, digest, size in rows:
            assert not name.startswith('/') and '..' not in Path(name).parts
            if name == record:
                assert digest == size == ''
            else:
                data = archive.read(name)
                expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
                assert digest == 'sha256=' + expected
                assert size == str(len(data))


def test_build_is_deterministic(tmp_path, base_dir):
    first = build_patch(base_dir, tmp_path / 'first')
    second = build_patch(base_dir, tmp_path / 'second')
    assert first.read_bytes() == second.read_bytes()


def test_bad_inventory_rejected(tmp_path):
    base = tmp_path / 'bad-base'
    info = base / 'semantica-0.7.0.dist-info'
    info.mkdir(parents=True)
    (info / 'RECORD').write_text('../../outside,sha256=invalid,1\n')
    with pytest.raises(ValueError):
        build_patch(base, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_tampered_source_rejected(tmp_path, base_dir):
    base = tmp_path / 'tampered'
    shutil.copytree(base_dir, base)
    (base / 'semantica' / '__init__.py').write_text('synthetic-tamper')
    with pytest.raises(ValueError):
        build_patch(base, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()
