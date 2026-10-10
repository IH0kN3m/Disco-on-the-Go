"""Conservative source-only distribution checks; not a legal clearance tool."""
from pathlib import PurePosixPath
import re

ROOT_FILES = {'.gitattributes', '.gitignore', 'AGENTS.md', 'LICENSE', 'Makefile', 'README.md', 'requirements.lock'}
# Original source files from earlier reachable commits remain auditable.
ROOT_FILES.update({'Package.swift','requirements-scenes.lock'})
SUFFIXES = {
    'tools': {'.py', '.java'}, 'runtime': {'.swift', '.cs', '.h', '.mm', '.cpp', '.S'},
    'tests': {'.py'}, 'docs': {'.md'}, 'analysis': {'.md'},
    'apps': {'.swift', '.mm', '.plist', '.pbxproj', '.xcscheme', '.java', '.xml'}, '.github': {'.yml', '.yaml', '.md'},
}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'personal absolute path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
    'device UDID': re.compile(r'\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}\b'),
    'embedded data URI': re.compile(r'data:[\w/+.-]+;base64,'),
}


def check_source(name, data, mode='100644', private_values=()):
    path = PurePosixPath(name)
    errors = []
    if path.is_absolute() or '..' in path.parts or '\\' in name or not path.parts:
        return ['unsafe repository path']
    allowed = name in ROOT_FILES or name == 'reference/README.md' or (len(path.parts) > 1 and path.suffix in SUFFIXES.get(path.parts[0], set()))
    if not allowed:
        errors.append('path is outside the public source allowlist')
    if mode not in ('100644', '100755'):
        errors.append('symlinks, submodules and non-files are not release inputs')
    if len(data) > 256 * 1024:
        errors.append('unexpectedly large source file')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return errors + ['non-UTF-8 content']
    if '\x00' in text:
        errors.append('binary content')
    if text.startswith('version https://git-lfs.github.com/spec/'):
        errors.append('LFS object requires separate review')
    for label, pattern in PATTERNS.items():
        if pattern.search(text):
            errors.append(label)
    if any(value and value in text for value in private_values):
        errors.append('local device/signing identifier')
    return errors
