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

BASE = Path('.cache/uv/archive-v0/MJdIOXhjvucbhRDB')
VERSION = '0.7.0+ontologyworkspace.1'


def test_patch_wheel_version_record_and_module(tmp_path):
    wheel = build_patch(BASE, tmp_path)
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        assert 'semantica/ontology/document.py' in names
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


def test_build_is_deterministic(tmp_path):
    first = build_patch(BASE, tmp_path / 'first')
    second = build_patch(BASE, tmp_path / 'second')
    assert first.read_bytes() == second.read_bytes()


def test_bad_inventory_rejected(tmp_path):
    base = tmp_path / 'bad-base'
    info = base / 'semantica-0.7.0.dist-info'
    info.mkdir(parents=True)
    (info / 'RECORD').write_text('../../outside,sha256=invalid,1\n')
    with pytest.raises(ValueError):
        build_patch(base, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_tampered_source_rejected(tmp_path):
    base = tmp_path / 'tampered'
    shutil.copytree(BASE, base)
    (base / 'semantica' / '__init__.py').write_text('synthetic-tamper')
    with pytest.raises(ValueError):
        build_patch(base, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()
