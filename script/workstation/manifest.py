"""The manifest: what a workstation installs, and by which route.

The manifest is the authority for delivery. A capability the manifest delivers
does not also need a per-item approval record in the catalogue, because the
manifest enforces the guarantees that record existed to provide: archive
packages come from the signed Ubuntu archive, third-party repositories pin
their signing key, and release binaries pin a version and SHA-256. A capability
the manifest does not deliver is still gated by the catalogue.
"""
import json
from pathlib import Path

from .config import ROOT

# Capability identifiers whose manifest entry is spelled differently, because
# Debian names the package differently or one entry delivers another.
ALIASES = {
    'aws-cli': 'awscli',
    'vscode': 'code',
    'google-chrome': 'google-chrome-stable',
    'slack': 'slack-desktop',
    'dbeaver': 'dbeaver-ce',
    'midnight-commander': 'mc',
    'mcedit': 'mc',
    'docker-engine': 'docker-ce',
    'docker-compose': 'docker-compose-plugin',
    'docker-buildx': 'docker-buildx-plugin',
    'containerd': 'containerd.io',
    'nvidia-driver': 'nvidia-driver-595-open',
    'font-inconsolata': 'fonts-inconsolata',
    'font-powerline': 'fonts-powerline',
    'font-jetbrains-mono-nerd': 'fonts-jetbrains-mono',
    'libvirt': 'libvirt-clients',
    'qemu': 'quickemu',
    'networkmanager-openvpn': 'network-manager-openvpn-gnome',
    'gnome-extension-manager': 'gnome-shell-extension-manager',
    'gnome-text-editor': 'gedit',
    'delta': 'git-delta',
    'fd': 'fd-find',
    'opentofu': 'tofu',
    'claude-code': 'claude',
    'python': 'uv',
    'git-lfs-filters': 'git-lfs',
    'gcloud-cli': 'google-cloud-cli',
    'gpg': 'gnupg',
    'uvx': 'uv',
}

FILES = ('packages', 'repositories', 'snaps', 'binaries', 'runtimes', 'shell')


def load(root=None):
    base = Path(root or ROOT) / 'manifest'
    return {name: json.loads((base / f'{name}.json').read_text()) for name in FILES}


def delivered(manifest):
    """Every name the manifest installs, with the route that installs it."""
    routes = {}
    for group, entries in manifest['packages']['groups'].items():
        for entry in entries:
            routes[entry['name']] = 'apt:' + entry['source']
    for snap in manifest['snaps']['snaps']:
        routes[snap['name']] = 'snap'
    for binary in manifest['binaries']['binaries']:
        routes[binary['id']] = 'binary'
    for agent in manifest['runtimes']['agents']:
        routes[agent['id']] = 'agent'
    # The runtime managers are declared deliveries in their own right: nvm
    # installs Node, SDKMAN installs the JVM toolchain, uv installs Python.
    for section in ('node', 'jvm', 'python'):
        manager = manifest['runtimes'].get(section, {}).get('manager')
        if manager:
            routes[manager] = 'runtime'
    for name in (manifest['shell']['prompt']['name'], manifest['shell']['history']['name']):
        routes.setdefault(name, 'apt:archive')
    return routes


def covers(routes, capability_id):
    """True when the manifest delivers this capability under any known spelling."""
    name = capability_id.split('/')[-1]
    return name in routes or ALIASES.get(name, name) in routes
