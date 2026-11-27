"""Host profiles: which parts of the host a run installs.

The operator chooses profiles (`--profiles desktop,gpu`). profiles/host.json maps
each one to manifest groups, and `firewall` to its stage. The base groups install
on every run. A selection with none of the desktop set is headless: it runs no
desktop playbook, snap, GNOME setting or VS Code step, and verify demands none.

Which profiles apply, in order: the ones given on the command line, else the
choice the last apply recorded, else the default. Recording the choice keeps a
headless machine headless when apply is re-run without `--profiles`, as
setup-dev-win and setup-dev-linux-wsl keep theirs. The record is per-user state
outside the clone (workstation/state.py), under the `profiles` key.
"""
from pathlib import Path

from .config import ROOT, InputError, load_json, require, validate_schema

CATALOGUE = 'profiles/host.json'
SCHEMA = 'profiles/host.schema.json'
HINT = './bootstrap apply --config <file> --profiles <list>'
# Catalogue boundaries that describe this repository's own tooling rather than
# the workstation: the controller apply runs on (its pinned Python, ansible-core,
# and the QA tools CI uses) and the disposable test VM. The controller-foundation
# check covers the first; neither is something a workstation lacks (D035).
REPOSITORY_BOUNDARIES = ('controller', 'test-vm')


def load(root=ROOT):
    """The validated profile catalogue, consistent with the manifest it maps."""
    root = Path(root)
    catalogue, _ = load_json(root / CATALOGUE)
    schema, _ = load_json(root / SCHEMA)
    validate_schema(catalogue, schema)
    names = set(catalogue['profiles'])
    require(set(catalogue['default']) <= names, 'unknown-default-profile')
    require(set(catalogue['desktop_set']) <= names, 'unknown-desktop-set-profile')
    require(set(catalogue['stages']) <= names, 'unknown-stage-profile')
    packages, _ = load_json(root / 'manifest/packages.json')
    owners = list(catalogue['base_groups'])
    for groups in catalogue['profiles'].values():
        owners.extend(groups)
    require(sorted(owners) == sorted(packages['groups']), 'manifest-group-without-one-profile')
    # Snaps are desktop software: none may install on a headless selection.
    desktop_groups = {g for p in catalogue['desktop_set'] for g in catalogue['profiles'][p]}
    snaps, _ = load_json(root / 'manifest/snaps.json')
    require(all(s['group'] in desktop_groups for s in snaps['snaps']), 'snap-outside-desktop-set')
    return catalogue


def available(catalogue):
    return list(catalogue['profiles'])


def parse(text, catalogue):
    """A comma-separated list as catalogue-ordered profile names."""
    names = [n.strip() for n in text.split(',') if n.strip()]
    require(names, 'no-profile-selected')
    require(len(names) == len(set(names)), 'duplicate-profile')
    valid = available(catalogue)
    # The error lists the valid names and never echoes what the operator typed.
    require(set(names) <= set(valid), 'unknown-profile; valid profiles: ' + ','.join(valid))
    return [n for n in valid if n in names]


def recorded():
    """The profiles the last apply recorded, or None when none were.

    A record that exists but cannot be read, or fails the state file's safety
    checks, is an error, not an absence: falling back to the default would
    install the desktop on a headless machine.
    """
    from . import state
    try:
        names = state.get('profiles')
    except InputError:
        raise InputError('recorded-profiles-unreadable; pass --profiles') from None
    if names is None:
        return None
    if not (isinstance(names, list) and names and all(isinstance(n, str) for n in names)):
        raise InputError('recorded-profiles-unreadable; pass --profiles')
    return names


def select(text, catalogue):
    """(profiles, source): explicit, else recorded, else the default."""
    if text is not None:
        return parse(text, catalogue), 'explicit'
    names = recorded()
    if names is not None:
        try:
            return parse(','.join(names), catalogue), 'recorded'
        except InputError:
            raise InputError('recorded-profiles-unreadable; pass --profiles') from None
    return list(catalogue['default']), 'default'


def resolve(names, catalogue, root=ROOT):
    """What a selection installs: manifest groups, repositories and extra stages."""
    groups = list(catalogue['base_groups'])
    for name in names:
        groups.extend(g for g in catalogue['profiles'][name] if g not in groups)
    packages, _ = load_json(Path(root) / 'manifest/packages.json')
    repositories, _ = load_json(Path(root) / 'manifest/repositories.json')
    sources = {e['source'] for g in groups for e in packages['groups'][g]}
    desktop = bool(set(names) & set(catalogue['desktop_set']))
    return {'profiles': list(names),
            'groups': groups,
            'repositories': [r['id'] for r in repositories['repositories'] if r['id'] in sources],
            'stages': [s for n in names for s in catalogue['stages'].get(n, [])],
            'desktop': desktop,
            'headless': not desktop}


def line(names, catalogue):
    """The operator-facing summary, in setup-dev-win's wording."""
    return (f"Profiles: {','.join(names)} (default {','.join(catalogue['default'])}; "
            f"available {','.join(available(catalogue))}; change with {HINT})")


def summary(names, source, catalogue):
    return {'selected': list(names), 'source': source, 'default': list(catalogue['default']),
            'available': available(catalogue), 'line': line(names, catalogue)}


def in_scope(capability_id, entry, selection, catalogue, groups=None):
    """Whether a catalogue capability belongs to the selection.

    A capability the manifest delivers belongs to the profile owning its
    manifest group (`groups`: name -> group, from manifest.delivering_groups).
    Anything else belongs to the host profile the catalogue mapping names, or
    to every selection when it names none. A capability owned by an unselected
    profile is not this machine's gap: a headless machine has not failed to
    receive a VS Code extension. Repository tooling (REPOSITORY_BOUNDARIES)
    belongs to no selection.
    """
    from .manifest import group_of
    if entry.get('boundary') in REPOSITORY_BOUNDARIES:
        return False
    group = group_of(groups or {}, capability_id)
    if group is not None:
        return group in selection['groups']
    mapping = catalogue['catalogue']
    owner = mapping['capabilities'].get(capability_id) or mapping['profiles'].get(entry.get('profile'))
    return owner is None or owner in selection['profiles']
