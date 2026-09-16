"""Reviewed system dependencies, activated only by selected approved capabilities."""
from .config import ROOT, load_json, require, validate_schema


def registry(entries=None, root=ROOT):
    value, _ = load_json(root / 'catalogue/prerequisites.json')
    validate_schema(value, load_json(root / 'catalogue/prerequisites.schema.json')[0])
    result = {}
    records = {}
    packages = {}
    for group in value['requirements']:
        capability = group['capability']
        require(capability not in result, 'duplicate-prerequisite-capability')
        if entries is not None:
            require(capability in entries and entries[capability]['kind'] == 'package' and
                    entries[capability]['delivery']['status'] == 'verified', 'unapproved-prerequisite-capability')
        require(len({r['id'] for r in group['packages']}) == len(group['packages']) and
                len({r['package'] for r in group['packages']}) == len(group['packages']), 'duplicate-prerequisite-package')
        for record in group['packages']:
            require(record['id'].startswith('dependency-') and (entries is None or record['id'] not in entries), 'invalid-prerequisite-id')
            require(record['id'] not in records or records[record['id']] == record, 'conflicting-prerequisite-id')
            require(record['package'] not in packages or packages[record['package']] == record, 'conflicting-prerequisite-package')
            records[record['id']] = record
            packages[record['package']] = record
        result[capability] = group['packages']
    return result


def selected_records(mapping, selected):
    return list({r['package']: r for capability in selected for r in mapping.get(capability, [])}.values())


def combine_records(records):
    result = {}
    for record in records:
        previous = result.get(record['package'])
        require(previous is None or (previous['source_package'] == record['source_package'] and
                previous['allowed_suites'] == record['allowed_suites']), 'conflicting-package-prerequisite')
        result.setdefault(record['package'], record)
    return list(result.values())
