#!/usr/bin/python3 -B
"""Internal distribution-Python APT adapter. Reads a request on stdin; never writes."""
import json
from pathlib import Path
import sys
import subprocess
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workstation.packages import allowed_version


def main():
    import apt
    records = json.load(sys.stdin)
    status = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}\t${db:Status-Status}\t${Version}\n',
                             *[r['package'] for r in records]], capture_output=True, text=True, timeout=30)
    if status.returncode not in (0, 1):
        raise ValueError('dpkg state unavailable')
    installed_state = {}
    for line in status.stdout.splitlines():
        name, state, version = line.split('\t')
        installed_state[name.split(':')[0]] = (state, version)
    cache = apt.Cache(memonly=True)
    result = []
    def describe(version):
        if not version:
            return None
        return {'source_package': version.source_name, 'architecture': version.architecture,
                'sha256': version.record.get('SHA256'),
                # "site" identifies the repository a version is served from, which
                # is what the manifest declares; origin labels differ per vendor.
                'origins': [{'origin': o.origin, 'suite': o.archive,
                             'site': o.site, 'trusted': o.trusted}
                            for o in version.origins if o.origin or o.archive != 'now']}
    import apt_pkg
    # version_compare needs the APT system initialised. "import apt" normally
    # does it as a side effect; doing it explicitly keeps this correct when the
    # cache is supplied rather than opened here.
    apt_pkg.init_system()

    def declared_candidate(package, record):
        """Highest version served by the source the manifest declares.

        APT's own candidate is the highest version across every configured
        repository, which is not necessarily the declared one: a second
        repository can ship the same package under a higher epoch and take it
        over silently. Choosing among the versions that actually come from the
        declared source is what makes that declaration mean anything.
        """
        if not package:
            return None
        matching = [v for v in package.versions if allowed_version(describe(v), record)]
        if not matching:
            return None
        best = matching[0]
        for version in matching[1:]:
            if apt_pkg.version_compare(version.version, best.version) > 0:
                best = version
        return best

    for record in records:
        package = cache.get(record['package'])
        chosen = declared_candidate(package, record)
        installed = package.installed if package else None
        # Match the installed version against actual repository metadata, not status alone.
        installed_versions = [v for v in package.versions if installed and v.version == installed.version] if package else []
        result.append({'id': record['id'], 'package': record['package'],
                       'candidate': chosen.version if chosen else None,
                       'apt_candidate': package.candidate.version if package and package.candidate else None,
                       'install_spec': record['package'] + '=' + chosen.version if chosen else None,
                       'install_allowed': chosen is not None,
                       'installed_allowed': bool(installed and installed_state.get(record['package']) == ('installed', installed.version)) and any(allowed_version(describe(v), record) for v in installed_versions)})
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (ImportError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Required distribution APT inspection failed', file=sys.stderr)
        raise SystemExit(2)
