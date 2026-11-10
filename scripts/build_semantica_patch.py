"""Build a real, deterministic Semantica local-version wheel from pinned source.

The original cache/installed environment is never modified. All base RECORD
hashes and patch hashes are checked before output directories are created.
"""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record_digest(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')


def build_patch(base_dir: Path, output_dir: Path) -> Path:
    manifest = json.loads((ROOT / 'patches/semantica/manifest.json').read_text(encoding='utf-8'))
    base = Path(base_dir).resolve(strict=True)
    old_info = f"semantica-{manifest['base_version']}.dist-info"
    new_info = f"semantica-{manifest['version']}.dist-info"
    inventory = base / old_info / 'RECORD'
    raw_record = inventory.read_bytes()
    if digest(raw_record) != manifest['base_record_sha256']:
        raise ValueError('Base inventory hash mismatch')
    payload = {}
    original_names = set()
    for name, expected, size in csv.reader(io.StringIO(raw_record.decode('utf-8'))):
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or name in original_names:
            raise ValueError('Unsafe or duplicate inventory path')
        original_names.add(name)
        resolved = (base / name).resolve(strict=True)
        if not resolved.is_relative_to(base) or not resolved.is_file():
            raise ValueError('Inventory source escapes base')
        data = resolved.read_bytes()
        if name == old_info + '/RECORD':
            if expected or size:
                raise ValueError('Invalid RECORD self reference')
            continue
        if expected != record_digest(data) or size != str(len(data)):
            raise ValueError('Base source hash or size mismatch')
        new_name = new_info + name[len(old_info):] if name.startswith(old_info + '/') else name
        payload[new_name] = data
    required = {'semantica/__init__.py', new_info + '/METADATA', new_info + '/WHEEL', new_info + '/licenses/LICENSE'}
    if not required.issubset(payload):
        raise ValueError('Missing source package or license')
    init, count = re.subn(rb'(?m)^__version__ = "0\.7\.0"$',
                         f'__version__ = "{manifest["version"]}"'.encode(), payload['semantica/__init__.py'])
    if count != 1:
        raise ValueError('Unexpected source version')
    payload['semantica/__init__.py'] = init
    metadata, count = re.subn(rb'(?m)^Version: 0\.7\.0$',
                             f'Version: {manifest["version"]}'.encode(), payload[new_info + '/METADATA'])
    if count != 1:
        raise ValueError('Unexpected distribution version')
    payload[new_info + '/METADATA'] = metadata
    for target, patch in manifest['patches'].items():
        if target in payload or PurePosixPath(target).is_absolute() or '..' in PurePosixPath(target).parts:
            raise ValueError('Patch target collision or unsafe path')
        source = (ROOT / patch['source']).resolve(strict=True)
        if not source.is_relative_to(ROOT / 'patches'):
            raise ValueError('Patch source outside approved directory')
        data = source.read_bytes()
        if digest(data) != patch['sha256']:
            raise ValueError('Patch source hash mismatch')
        payload[target] = data
    payload['semantica/ontology/ontologyworkspace_patch.json'] = json.dumps(manifest, sort_keys=True, indent=2).encode()
    record_path = new_info + '/RECORD'
    output_record = io.StringIO(newline='')
    writer = csv.writer(output_record, lineterminator='\n')
    for name, data in sorted(payload.items()):
        writer.writerow([name, record_digest(data), len(data)])
    writer.writerow([record_path, '', ''])
    payload[record_path] = output_record.getvalue().encode()
    output = Path(output_dir)
    filename = f'semantica-{manifest["version"]}-py3-none-any.whl'
    wheel = output / filename
    if wheel.exists():
        raise ValueError('Refusing to overwrite an existing wheel')
    output.mkdir(parents=True, exist_ok=True)
    with wheel.open('xb') as handle:
        with ZipFile(handle, 'w', compression=ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
    return wheel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wheel = build_patch(args.base, args.output)
    print(wheel)
    print('sha256:', digest(wheel.read_bytes()))


if __name__ == '__main__':
    main()
