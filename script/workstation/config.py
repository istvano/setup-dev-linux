"""Strict, read-only input validation shared by runtime commands and static QA."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


class InputError(ValueError):
    """Message is a fixed public error code, never untrusted input."""


def require(condition, code):
    if not condition:
        raise InputError(code)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def load_json(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
        require(len(raw) <= 4 * 1024 * 1024, 'input-too-large')
        def nonfinite(_):
            raise InputError('nonfinite-json-number')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_constant=nonfinite)
        return value, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise InputError('unreadable-or-invalid-json') from None


KEYWORDS = {'$schema', 'type', 'properties', 'additionalProperties', 'required',
            'items', 'enum', 'const', 'minimum', 'minItems', 'uniqueItems',
            'minLength', 'pattern'}
TYPES = {'object': dict, 'array': list, 'string': str, 'integer': int,
         'boolean': bool, 'null': type(None)}


def validate_schema(value, schema):
    """Exact supported subset of committed input schemas, failing on new vocabulary."""
    require(not (set(schema) - KEYWORDS), 'unsupported-schema-keyword')
    kinds = schema.get('type')
    if kinds:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        require(all(k in TYPES for k in kinds), 'unsupported-schema-type')
        require(any(type(value) is TYPES[k] for k in kinds), 'schema-type')
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'], 'schema-const')
    if 'enum' in schema:
        require(any(type(value) is type(v) and value == v for v in schema['enum']), 'schema-enum')
    if type(value) is dict:
        props = schema.get('properties', {})
        require(set(schema.get('required', [])) <= value.keys(), 'schema-required')
        if schema.get('additionalProperties') is False:
            require(set(value) <= props.keys(), 'schema-unknown-field')
        for key in value.keys() & props.keys():
            validate_schema(value[key], props[key])
    elif type(value) is list:
        require(len(value) >= schema.get('minItems', 0), 'schema-min-items')
        if schema.get('uniqueItems'):
            serial = [json.dumps(v, sort_keys=True) for v in value]
            require(len(serial) == len(set(serial)), 'schema-duplicate-item')
        if 'items' in schema:
            for item in value:
                validate_schema(item, schema['items'])
    elif type(value) is str:
        require(len(value) >= schema.get('minLength', 0), 'schema-min-length')
        if 'pattern' in schema:
            require(re.search(schema['pattern'], value) is not None, 'schema-pattern')
    elif type(value) is int and 'minimum' in schema:
        require(value >= schema['minimum'], 'schema-minimum')


def validate_semantics(config, entries, selected):
    require(len(selected) == len(set(selected)), 'duplicate selected ID')
    require(set(selected) <= entries.keys(), 'unknown selected capability')
    require('python' not in selected or 'uv' in selected, 'python-requires-selected-uv')
    require(all(entries[i]['decision'] not in ('pending', 'omit') for i in selected), 'pending/omitted capability selected')
    require(all(not (set(entries[i]['conflicts']) & set(selected)) for i in selected), 'conflicting selected capabilities')
    storage = config['storage']
    disks, mounts = storage['disks'], storage['mounts']
    split = storage['layout'] == 'split'
    require(set(disks) == ({'system', 'data'} if split else {'system'}), 'disk roles contradict layout')
    require(split or not storage['separate_var_lib'], 'single disk cannot select separate /var/lib')
    require(('/var/lib' in mounts) == storage['separate_var_lib'], '/var/lib mount contradicts selection')
    require(len({d['stable_id'] for d in disks.values()}) == len(disks), 'duplicate physical disk identities')
    require(len({m['filesystem_uuid'] for m in mounts.values()}) == len(mounts), 'duplicate mount UUIDs')
    for path, mount in mounts.items():
        expected = 'data' if split and path in ('/home', '/var/lib') else 'system'
        require(mount['disk_role'] == expected, 'wrong disk role for mount')
    gpu = {i for i, item in entries.items() if item['profile'] == 'gpu'}
    require((set(selected) & gpu) == (gpu if config['features']['gpu'] == 'nvidia' else set()), 'GPU feature/selection mismatch')
    if not config['example_only']:
        require('REPLACE' not in json.dumps(config), 'operational input contains placeholders')
        require(all(d['minimum_bytes'] is not None for d in disks.values()), 'operational capacity missing')
        require(config['target']['user'] != 'root', 'root target user forbidden')
        require(re.fullmatch(r'[a-z_][a-z0-9_-]*', config['target']['user']) is not None, 'invalid-target-user')
        require(all(d['stable_id'].startswith('/dev/disk/by-id/') and '..' not in Path(d['stable_id']).parts for d in disks.values()), 'stable-disk-id-required')


def load_context(path):
    path = Path(path).absolute()
    config, config_hash = load_json(path)
    schema, _ = load_json(ROOT / 'config/workstation.schema.json')
    validate_schema(config, schema)
    selection, selection_hash = load_json(path.parent / config['selection_file'])
    schema, _ = load_json(ROOT / 'profiles/selection.schema.json')
    validate_schema(selection, schema)
    catalogue, _ = load_json(ROOT / 'catalogue/capabilities.json')
    schema, _ = load_json(ROOT / 'catalogue/capabilities.schema.json')
    validate_schema(catalogue, schema)
    entries = {e['id']: e for e in catalogue['capabilities']}
    require(len(entries) == len(catalogue['capabilities']), 'duplicate-catalogue-id')
    validate_semantics(config, entries, selection['capability_ids'])
    from .packages import approved_registry
    approved = approved_registry(entries)
    from .artifacts import registry
    user_tools = registry(entries)
    from .node_runtime import node_lock
    node_lock(entries)
    from .sdkman_runtime import manager_lock
    manager_lock(entries)
    from .java_runtime import java_lock
    java_lock(entries)
    from .jvm_tools import tool_lock
    tool_lock(entries)
    from .mandrel_runtime import mandrel_lock
    mandrel_lock(entries)
    from .go_runtime import go_lock
    go_lock(entries)
    from .rust_runtime import rust_lock
    rust_lock(entries)
    from .python_user import python_lock
    python_lock(entries)
    from .opencode_runtime import opencode_lock
    opencode_lock(entries)
    from .codex_runtime import codex_lock
    codex_lock(entries)
    from .cline_runtime import cline_lock
    cline_lock(entries)
    from .prerequisites import registry as prerequisite_registry
    prerequisite_map = prerequisite_registry(entries)
    from .user_environment import settings
    private = settings(path.parent / config['user_settings_file']) if config.get('user_settings_file') else {}
    return {'config': config, 'entries': entries, 'selected': selection['capability_ids'],
            'approved': approved, 'prerequisites': prerequisite_map, 'user_tools': user_tools, 'user_settings': private,
            'provenance': {'config_sha256': config_hash, 'selection_sha256': selection_hash,
                           'catalogue_revision': catalogue['revision'],
                           'user_settings_sha256': hashlib.sha256(json.dumps(private, sort_keys=True).encode()).hexdigest() if private else None}}
