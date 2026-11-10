"""Bounded JSON contracts and contained artifact checks. No source execution."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
import yaml

SCHEMAS = Path(__file__).resolve().parents[1] / 'contracts'
KINDS = {'scenario-pack','validation-result','release-manifest','backend-operation'}
MAX_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


def error(pointer, code, message):
    return {'pointer':pointer, 'code':code, 'message':message}


def pointer(parts):
    return ''.join('/'+str(part).replace('~','~0').replace('/','~1') for part in parts)


def bounded_json(value):
    pending = [value]; seen = set(); count = 0
    while pending:
        current = pending.pop(); count += 1
        if count > 10000:
            return False
        if type(current) in (dict,list):
            if id(current) in seen:
                return False
            seen.add(id(current))
            if type(current) is dict:
                if not all(type(key) is str for key in current):
                    return False
                pending.extend(current.values())
            else:
                pending.extend(current)
        elif type(current) not in (str,int,float,bool,type(None)):
            return False
        elif type(current) is float and not math.isfinite(current):
            return False
    return True


def validate_document(kind: str, document: dict) -> list[dict]:
    if kind not in KINDS or type(document) is not dict or not bounded_json(document):
        return [error('', 'INVALID_DOCUMENT', 'Unsupported or invalid contract document')]
    registry = Registry()
    schemas = {}
    for name in sorted(KINDS | {'common'}):
        data = json.loads((SCHEMAS / (name+'.schema.json')).read_text(encoding='utf-8'))
        schemas[name] = data
        registry = registry.with_resource(data['$id'], Resource.from_contents(data))
    validator = Draft202012Validator(schemas[kind], registry=registry, format_checker=FormatChecker())
    findings = []
    def collect(item):
        if item.context:
            for child in item.context:
                collect(child)
        else:
            code = 'SCHEMA_REQUIRED' if item.validator == 'required' else 'SCHEMA_INVALID'
            findings.append(error(pointer(item.absolute_path),code,'Contract field is missing or invalid'))
    for item in validator.iter_errors(document):
        collect(item)
    if kind == 'scenario-pack' and not findings:
        if document['version'].split('.')[0] != '1':
            findings.append(error('/version','PACK_VERSION_UNSUPPORTED','Unsupported pack major version'))
        ids = [source['id'] for source in document['sources']]
        if len(ids) != len(set(ids)):
            findings.append(error('/sources','DUPLICATE_SOURCE_ID','Source identifiers must be unique'))
    return findings


def safe_file(root, value, at):
    if type(value) is not str or not value or '\\' in value or '\x00' in value:
        return None, error(at,'PATH_UNSAFE','Artifact path must be a relative POSIX path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('','..','.') for part in value.split('/')) or re.match(r'^[A-Za-z]:',value):
        return None, error(at,'PATH_UNSAFE','Artifact path must be a relative POSIX path')
    try:
        target = (root / value).resolve()
        if not target.is_relative_to(root):
            return None, error(at,'PATH_ESCAPE','Artifact path escapes the allowed root')
        if not target.is_file():
            return None, error(at,'PATH_MISSING','Artifact file does not exist')
    except (OSError,ValueError,RuntimeError):
        return None, error(at,'PATH_UNSAFE','Artifact path cannot be resolved safely')
    return target, None


def validate_pack_paths(root: Path, manifest: dict) -> list[dict]:
    findings = validate_document('scenario-pack',manifest)
    if findings:
        return findings
    root = Path(root).resolve()
    paths = [(key,manifest[key]) for key in ('ontology_entrypoint','constraints_entrypoint','mappings','rules','competency_questions','expected','evaluation') if key in manifest]
    paths += [(f'sources/{index}/path',source['path']) for index,source in enumerate(manifest['sources'])]
    for key,value in paths:
        _, issue = safe_file(root,value,'/'+key)
        if issue:
            findings.append(issue)
    return findings


def verify_release_files(root: Path, manifest: dict) -> list[dict]:
    findings = validate_document('release-manifest',manifest)
    if findings:
        return findings
    root = Path(root).resolve(); seen = set()
    for index,artifact in enumerate(manifest['artifacts']):
        at = f'/artifacts/{index}/path'
        file,issue = safe_file(root,artifact['path'],at)
        if issue:
            findings.append(issue); continue
        if file in seen:
            findings.append(error(at,'DUPLICATE_ARTIFACT_PATH','Artifact paths must be unique')); continue
        seen.add(file)
        size = file.stat().st_size
        if size != artifact['size'] or size > MAX_ARTIFACT_BYTES:
            findings.append(error(at,'SIZE_MISMATCH','Artifact size does not match manifest')); continue
        digest = hashlib.sha256()
        with file.open('rb') as stream:
            while chunk := stream.read(65536):
                digest.update(chunk)
        if digest.hexdigest() != artifact['sha256']:
            findings.append(error(at,'HASH_MISMATCH','Artifact hash does not match manifest'))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',required=True,choices=sorted(KINDS))
    parser.add_argument('--file',type=Path,required=True)
    args = parser.parse_args()
    try:
        if args.file.stat().st_size > MAX_BYTES:
            raise ValueError('Input too large')
        text = args.file.read_text(encoding='utf-8')
        data = yaml.safe_load(text) if args.file.suffix in ('.yaml','.yml') else json.loads(text)
        findings = validate_document(args.kind,data)
    except (OSError,ValueError,UnicodeError,yaml.YAMLError,RecursionError):
        findings = [error('','INVALID_DOCUMENT','Contract document cannot be read safely')]
    print(json.dumps(findings,ensure_ascii=False))
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
