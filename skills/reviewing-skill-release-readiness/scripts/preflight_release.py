#!/usr/bin/env python3
"""Read-only candidate package preflight: findings, never publication approval.

Designed for Python >=3.10, standard library only. No network, extraction or
mutation. It does not prove provenance, legal rights, model behaviour or security.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FILES = 4000
MAX_ARCHIVE_BYTES = 80 * 1024 * 1024
TEXT_SUFFIXES = {'.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.py', '.js', '.ts', '.tsx', '.sh', '.ps1', '.ini', '.cfg', '.csv', '.env', '.xml'}
ASSET_SUFFIXES = {'.pdf', '.ppt', '.pptx', '.doc', '.docx', '.xlsx', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ttf', '.otf', '.woff', '.woff2', '.glb', '.stl', '.mp3', '.mp4'}
LICENCE_NAMES = {'license', 'licence', 'license.md', 'licence.md', 'license.txt', 'licence.txt', 'copying', 'copying.md'}
SECRET_ASSIGNMENT = re.compile(r'\b(?:API[_-]?KEY|OPENAI_API_KEY|AUTH_TOKEN|ACCESS_TOKEN|PRIVATE_KEY|PASSWORD|CLIENT_SECRET|GH_TOKEN)\s*[:=]\s*["\']?([^\s"\';,#]+)', re.IGNORECASE)
BEARER_TOKEN = re.compile(r'\bBearer\s+[a-zA-Z0-9_.\-]{15,}\b')
EMAIL = re.compile(r'(?<![\w.-])[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}')
LOCAL_PATH = re.compile(r'(?:[A-Za-z]:\\Users\\[^\\/\s]+|/home/(?:[^/\s]+)|/Users/(?:[^/\s]+))')


def finding(code, level, path=None, line=None, note=None):
    record = {'code': code, 'level': level}
    if path is not None:
        record['path'] = path
    if line is not None:
        record['line'] = line
    if note is not None:
        record['action'] = note
    return record


def read_directory(root: Path, findings):
    # Never follow any symbolic link, including directory symlinks.
    if root.is_symlink():
        raise ValueError('Input root is a symlink; provide a real directory or archive.')
    files = {}
    count = 0
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        basedir = Path(current)
        kept = []
        for d in sorted(directories):
            p = basedir / d
            if p.is_symlink():
                findings.append(finding('SYMLINK_UNSUPPORTED', 'HOLD', p.relative_to(root).as_posix(), note='Remove or replace the symlink; no target was followed.'))
            else:
                kept.append(d)
        directories[:] = kept
        for name in sorted(filenames):
            p = basedir / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                findings.append(finding('SYMLINK_UNSUPPORTED', 'HOLD', rel, note='Remove or replace the symlink; no target was followed.'))
                continue
            count += 1
            if count > MAX_FILES:
                findings.append(finding('TOO_MANY_FILES', 'HOLD', note='Narrow the candidate package and review separately.'))
                return files
            try:
                length = p.stat().st_size
                if length > MAX_FILE_BYTES:
                    # Still hash every byte without loading or content-scanning huge files.
                    hasher = hashlib.sha256()
                    with p.open('rb') as stream:
                        for chunk in iter(lambda: stream.read(64 * 1024), b''):
                            hasher.update(chunk)
                    files[rel] = {'sha256': hasher.hexdigest(), 'body': None, 'size': length}
                    findings.append(finding('FILE_TOO_LARGE_FOR_CONTENT_SCAN', 'REVIEW', rel, note='Review this file independently.'))
                    continue
                body = p.read_bytes()
                files[rel] = {'sha256': hashlib.sha256(body).hexdigest(), 'body': body, 'size': length}
            except (PermissionError, OSError):
                findings.append(finding('FILE_UNREADABLE', 'HOLD', rel, note='Fix read access to complete preflight.'))
    return files


def read_zip(path: Path, findings):
    files = {}
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive is over the configured bounded scan size.')
    if not zipfile.is_zipfile(path):
        raise ValueError('The input is not a readable ZIP archive.')
    with zipfile.ZipFile(path) as z:
        info = z.infolist()
        if len(info) > MAX_FILES + 100:
            findings.append(finding('TOO_MANY_FILES', 'HOLD', note='Narrow the archive and review separately.'))
            return files
        roots = set()
        for member in info:
            raw = member.filename
            segments = raw.replace('\\', '/').split('/')
            bad = (raw.startswith('/') or '\\' in raw or any(seg in {'..', '.'} for seg in segments)
                   or (segments and re.match(r'^[A-Za-z]:', segments[0])) or '\x00' in raw)
            if bad:
                findings.append(finding('UNSAFE_ARCHIVE_PATH', 'HOLD', note='Rebuild the archive with safe contained paths.'))
                continue
            if not member.is_dir() and raw:
                roots.add(segments[0])
        # Plugin archives are conventionally packed with one top-level directory.
        wrapped = len(roots) == 1 and 'plugin.json' not in roots and 'SKILL.md' not in roots
        if not wrapped:
            findings.append(finding('ARCHIVE_ROOT_INVALID', 'HOLD', note='Build one archive containing exactly one plugin or skill directory.'))
        total_uncompressed = 0
        for member in info:
            if member.is_dir():
                continue
            raw = member.filename
            parts = raw.replace('\\', '/').split('/')
            if (raw.startswith('/') or '\\' in raw or any(x in {'.', '..'} for x in parts)
                    or (parts and re.match(r'^[A-Za-z]:', parts[0])) or '\x00' in raw):
                continue
            mode = (member.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                findings.append(finding('SYMLINK_UNSUPPORTED', 'HOLD', note='Remove archived symlinks.'))
                continue
            rel = '/'.join(parts[1:]) if wrapped else '/'.join(parts)
            if not rel:
                continue
            total_uncompressed += member.file_size
            if total_uncompressed > MAX_ARCHIVE_BYTES:
                findings.append(finding('ARCHIVE_SIZE_LIMIT', 'HOLD', note='Archive uncompressed content exceeds safe preflight bounds.'))
                break
            if member.file_size > MAX_FILE_BYTES:
                findings.append(finding('FILE_TOO_LARGE_FOR_CONTENT_SCAN', 'REVIEW', rel))
                try:
                    hasher = hashlib.sha256()
                    with z.open(member) as stream:
                        for chunk in iter(lambda: stream.read(64 * 1024), b''):
                            hasher.update(chunk)
                    files[rel] = {'sha256': hasher.hexdigest(), 'body': None, 'size': member.file_size}
                except (RuntimeError, OSError, zipfile.BadZipFile):
                    findings.append(finding('ARCHIVE_MEMBER_UNREADABLE', 'HOLD', rel))
                continue
            try:
                body = z.read(member)
            except (RuntimeError, OSError, zipfile.BadZipFile):
                findings.append(finding('ARCHIVE_MEMBER_UNREADABLE', 'HOLD', rel))
                continue
            if rel in files:
                findings.append(finding('DUPLICATE_ARCHIVE_PATH', 'HOLD', rel, note='Remove repeated paths that may hide replacement content.'))
                continue
            files[rel] = {'sha256': hashlib.sha256(body).hexdigest(), 'body': body, 'size': member.file_size}
    return files


def text_of(file):
    if file['body'] is None:
        return ''
    return file['body'].decode('utf-8', errors='replace')


def validate(files, findings):
    paths = set(files)
    root_manifest = 'plugin.json' in paths
    skill_paths = sorted(p for p in paths if p == 'SKILL.md' or (p.startswith('skills/') and p.endswith('/SKILL.md') and p.count('/') == 2))
    if not root_manifest and 'SKILL.md' not in paths:
        findings.append(finding('ENTRYPOINT_MISSING', 'HOLD', note='Include root plugin.json and skills, or standalone SKILL.md.'))
    if root_manifest:
        try:
            obj = json.loads(text_of(files['plugin.json']))
            version = obj['version']
            name = obj['name']
            if not (isinstance(version, str) and re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.+-]+)?', version)):
                raise ValueError('Version must be SemVer')
            if not (isinstance(name, str) and re.fullmatch('[a-z][a-z0-9-]{0,63}', name)):
                raise ValueError('Name must be lowercase kebab-case')
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            findings.append(finding('MANIFEST_INVALID', 'HOLD', 'plugin.json', note='Provide a valid name and semantic version.'))
            name = version = None
        if '.codex-plugin/plugin.json' in paths:
            try:
                compat = json.loads(text_of(files['.codex-plugin/plugin.json']))
                if compat.get('version') != version:
                    findings.append(finding('VERSION_MISMATCH', 'HOLD', '.codex-plugin/plugin.json', note='Synchronise release versions.'))
                if compat.get('name') != name:
                    findings.append(finding('PACKAGE_NAME_MISMATCH', 'HOLD', '.codex-plugin/plugin.json', note='Synchronise package names.'))
            except json.JSONDecodeError:
                findings.append(finding('COMPAT_MANIFEST_INVALID', 'HOLD', '.codex-plugin/plugin.json'))
        if 'VERSION' in paths and text_of(files['VERSION']).strip() != version:
            findings.append(finding('VERSION_MISMATCH', 'HOLD', 'VERSION', note='Synchronise candidate versions.'))
    if not skill_paths:
        findings.append(finding('SKILL_ENTRYPOINT_MISSING', 'HOLD', note='Include discoverable SKILL.md with frontmatter.'))
    for path in skill_paths:
        content = text_of(files[path])
        m = re.match(r'\A---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not m:
            findings.append(finding('SKILL_FRONTMATTER_MISSING', 'HOLD', path))
            continue
        front = m.group(1)
        nm = re.search(r'^name:\s*(.+?)\s*$', front, re.MULTILINE)
        desc = re.search(r'^description:\s*(.+?)\s*$', front, re.MULTILINE)
        expected = Path(path).parent.name if path != 'SKILL.md' else None
        if not nm or not desc or (expected and nm.group(1).strip('"\'') != expected):
            findings.append(finding('SKILL_FRONTMATTER_INVALID', 'HOLD', path, note='Include a matching name and a selective description.'))
    if not any(p.lower() in LICENCE_NAMES for p in paths):
        findings.append(finding('LICENCE_MISSING', 'HOLD', note='Declare a suitable permission grant for content you own, or resolve distribution rights.'))
    if 'README.md' not in paths:
        findings.append(finding('README_MISSING', 'HOLD', note='Explain install, prerequisites, use, limits, and verification.'))
    tests = [p for p in paths if ('/tests/' in '/'+p or '/test_' in '/'+p) and p.lower().endswith(('.py', '.md', '.json', '.js', '.ts', '.yaml'))]
    if not tests:
        findings.append(finding('TEST_ARTIFACTS_MISSING', 'HOLD', note='Provide behaviour scenarios and reproducible execution or review evidence.'))
    if any(Path(p).suffix.lower() in ASSET_SUFFIXES for p in paths):
        findings.append(finding('THIRD_PARTY_ASSETS_REVIEW', 'REVIEW', note='Check ownership and licences of examples, fonts, PDFs, images and other assets.'))
    if any(p in paths for p in ('mcp.json', 'requirements.txt', 'package.json')):
        findings.append(finding('DEPENDENCIES_NEED_RUNTIME_PROOF', 'REVIEW', note='Run installation and capability checks in a clean supported host.'))
    for path in sorted(paths):
        obj = files[path]
        if obj['body'] is None or Path(path).suffix.lower() not in TEXT_SUFFIXES:
            continue
        # Scan line by line; never echo matched sensitive contents.
        for line_no, line in enumerate(text_of(obj).splitlines(), 1):
            secret = SECRET_ASSIGNMENT.search(line)
            if secret:
                value = secret.group(1).strip()
                if value not in {'', '${', '...', '***', 'REDACTED', 'YOUR_KEY', 'YOUR_TOKEN', 'PLACEHOLDER'} and not value.startswith(('$', '{', '<', 'process.env.', 'os.environ', 'os.getenv', '%')):
                    findings.append(finding('POSSIBLE_SECRET', 'HOLD', path, line_no, 'Check for credential exposure and rotate any actual secret.'))
            if BEARER_TOKEN.search(line):
                findings.append(finding('POSSIBLE_SECRET', 'HOLD', path, line_no, 'Check for credential exposure and rotate any actual secret.'))
            if EMAIL.search(line):
                findings.append(finding('PERSONAL_INFORMATION_REVIEW', 'REVIEW', path, line_no, 'Confirm contact details are intended for public release.'))
            if LOCAL_PATH.search(line):
                findings.append(finding('MACHINE_SPECIFIC_PATH', 'REVIEW', path, line_no, 'Remove personal paths or document portable configuration.'))
    findings.append(finding('CHECK_RIGHTS_PROVENANCE', 'REVIEW', note='Human review must verify licences, borrowed material, curriculum extracts and permission to distribute.'))
    findings.append(finding('CHECK_EMPIRICAL_BEHAVIOUR', 'REVIEW', note='Run independent no-skill and with-skill scenarios, test a clean host, and review evidence.'))
    findings.append(finding('CHECK_OWNER_APPROVAL', 'REVIEW', note='Explicit owner approval is required before publishing or updating shared instructions.'))


def scan(source: Path):
    if not source.exists():
        return {'overall': 'BLOCKED_INPUT', 'error': 'The selected source does not exist.', 'findings': [], 'file_count': 0, 'artifact_sha256': None}, 2
    findings = []
    try:
        if source.is_dir():
            files = read_directory(source, findings)
        elif source.is_file() and source.suffix.lower() == '.zip':
            files = read_zip(source, findings)
        else:
            raise ValueError('Input must be a directory or ZIP archive.')
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return {'overall': 'BLOCKED_INPUT', 'error': str(exc), 'findings': [], 'file_count': 0, 'artifact_sha256': None}, 2
    validate(files, findings)
    digester = hashlib.sha256()
    for name in sorted(files):
        rec = files[name]
        digester.update(name.encode('utf-8') + b'\0')
        digester.update((rec['sha256'] or 'UNREADABLE').encode('ascii') + b'\n')
    findings.sort(key=lambda f: (f['level'] != 'HOLD', f['code'], f.get('path', ''), f.get('line', 0)))
    return {
        'overall': 'HOLD_AUTOMATED_FINDINGS' if any(f['level'] == 'HOLD' for f in findings) else 'MANUAL_REVIEW_REQUIRED',
        'artifact_sha256': digester.hexdigest(),
        'file_count': len(files),
        'findings': findings,
        'limitation': 'Heuristic, read-only static preflight. Never proof of safety, ownership, runtime behaviour or publication permission.',
    }, 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Exact skill/plugin directory or ZIP archive to inspect (read-only)')
    args = parser.parse_args()
    output, code = scan(Path(args.source))
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
