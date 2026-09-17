"""Finite chezmoi-owned user files, conflict handling and independent verification."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import shlex
import subprocess
import tempfile
import uuid
from .config import ROOT, InputError, load_json, require, validate_schema
from .artifacts import destination, safe_path, validate_payload

BEHAVIORS = {'shell-integration', 'git-identity', 'git-lfs-filters'}
BEGIN = '# BEGIN linux-os-setup managed include'
END = '# END linux-os-setup managed include'


def settings(path):
    require(not path.is_symlink(), 'unsafe-user-settings')
    info = path.stat()
    require(info.st_uid == os.geteuid() and not info.st_mode & 0o077, 'user-settings-must-be-private')
    value, _ = load_json(path)
    schema, _ = load_json(ROOT / 'config/user-settings.schema.json')
    validate_schema(value, schema)
    identities = value.get('identities', [])
    require(len({i['scope'] for i in identities}) == len(identities), 'duplicate-identity-scope')
    for identity in identities:
        require(Path(identity['directory']).is_absolute() and '..' not in Path(identity['directory']).parts and not any(c in identity['directory'] for c in '*?[]'), 'invalid-identity-directory')
        require(all(not any(ord(c) < 32 or ord(c) == 127 for c in text) for text in identity.values()), 'invalid-identity-value')
    directories = [Path(i['directory']).resolve() for i in identities]
    require(all(not a.is_relative_to(b) and not b.is_relative_to(a) for n, a in enumerate(directories) for b in directories[n+1:]), 'overlapping-identity-directories')
    return value


def merge_include(original, body):
    block = BEGIN + '\n' + body.rstrip('\n') + '\n' + END + '\n'
    if BEGIN not in original and END not in original:
        return original + ('' if not original or original.endswith('\n') else '\n') + block
    require(original.count(BEGIN) == original.count(END) == 1, 'conflicting-managed-markers')
    start, end = original.index(BEGIN), original.index(END)
    require(start < end and (start == 0 or original[start-1] == '\n'), 'conflicting-managed-markers')
    end += len(END)
    require(end == len(original) or original[end] == '\n', 'conflicting-managed-markers')
    return original[:start] + block + original[end + (end < len(original)):]


def read_owned(home, relative):
    path = home / relative
    safe_path(home, path)
    return path.read_text() if path.exists() else ''


def render(home, selected, private, tools, root=ROOT):
    files, owners, deferred = {}, {}, []
    def add(relative, content, owner):
        safe_path(home, home / relative)
        files[relative] = content
        owners.setdefault(owner, []).append(relative)
    if 'shell-integration' in selected:
        deps = {'chezmoi', 'oh-my-zsh', 'zsh', 'zsh-autosuggestions', 'zsh-syntax-highlighting'}
        if not deps <= set(selected):
            deferred.append('shell-integration')
        else:
            omz = destination(home, tools['oh-my-zsh']) / Path(tools['oh-my-zsh']['entrypoint']).parent
            executable_dirs = [str((destination(home, tools[key]) / tools[key]['entrypoint']).parent) for key in ['chezmoi', 'pnpm'] if key in selected]
            if 'go' in selected:
                from .go_runtime import go_lock
                go = go_lock()
                executable_dirs.append(str((destination(home, go) / go['entrypoint']).parent))
            if {'uv', 'python'} & set(selected):
                from .python_user import python_lock
                uv, python = python_lock()
                if 'uv' in selected:
                    executable_dirs.append(str((destination(home, uv) / uv['entrypoint']).parent))
                if 'python' in selected:
                    executable_dirs.append(str((destination(home, python) / python['entrypoint']).parent))
            if 'opencode' in selected:
                from .opencode_runtime import opencode_lock
                opencode = opencode_lock()
                executable_dirs.append(str((destination(home, opencode) / opencode['entrypoint']).parent))
            if 'codex' in selected:
                from .codex_runtime import codex_lock
                codex = codex_lock()
                executable_dirs.append(str((destination(home, codex) / codex['entrypoint']).parent))
            if 'cline' in selected:
                from .cline_runtime import cline_lock
                _, cline = cline_lock()
                executable_dirs.append(str((destination(home, cline) / cline['entrypoint']).parent))
            rust = None
            if 'rust' in selected:
                from .rust_runtime import rust_lock, state_root
                rust = rust_lock()
                executable_dirs.append(str(state_root(home, rust) / 'cargo/bin'))
            runtime_lines = ['typeset -U path', 'path=(' + ' '.join(shlex.quote(p) for p in executable_dirs) + ' $path)']
            if 'uv' in selected:
                runtime_lines.append('export UV_PYTHON_DOWNLOADS=never')
            if 'python' in selected:
                runtime_lines.append('export UV_PYTHON_INSTALL_DIR=' +
                                     shlex.quote(str(destination(home, python))))
            if 'opencode' in selected:
                runtime_lines.append('export OPENCODE_DISABLE_AUTOUPDATE=1')
            # The managed shell sets ZSH_THEME="", so the prompt has to be
            # started explicitly: the configuration file alone renders nothing.
            if 'starship' in selected:
                runtime_lines.append('command -v starship >/dev/null && '
                                     'eval "$(starship init zsh)"')
            if 'atuin' in selected:
                runtime_lines.append('command -v atuin >/dev/null && '
                                     'eval "$(atuin init zsh)"')
            if rust:
                rust_root = state_root(home, rust)
                runtime_lines += [
                    'export CARGO_HOME=' + shlex.quote(str(rust_root / 'cargo')),
                    'export RUSTUP_HOME=' + shlex.quote(str(rust_root / 'rustup')),
                ]
            if 'nvm' in selected:
                manager = destination(home, tools['nvm']) / tools['nvm']['entrypoint']
                runtime_lines += ['export NVM_DIR="$HOME/.local/share/linux-os-setup/nvm"', 'source ' + shlex.quote(str(manager)) + ' --no-use || return 1']
                if 'node' in selected:
                    runtime_lines.append('nvm use --silent default || return 1')
            if 'sdkman' in selected:
                runtime_lines += ['export SDKMAN_DIR="$HOME/.local/share/linux-os-setup/sdkman"', 'source "$SDKMAN_DIR/bin/sdkman-init.sh" || return 1']
            shell = '\n'.join([
                '# Managed shell integration; preserve unrelated .zshrc content.',
                '[[ ${_WORKSTATION_SHELL_LOADED:-0} == 1 ]] && return',
                '[[ -r /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh && -r /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] || return 1',
                'export ZSH=' + shlex.quote(str(omz)),
                'ZSH_CACHE_DIR="$HOME/.cache/linux-os-setup/oh-my-zsh"',
                'ZSH_COMPDUMP="$ZSH_CACHE_DIR/.zcompdump"',
                'ZSH_CUSTOM="$HOME/.config/linux-os-setup/oh-my-zsh-custom"',
                'zstyle ":omz:update" mode disabled',
                'DISABLE_AUTO_UPDATE=true',
                'ZSH_THEME=""', 'plugins=(git)', 'source "$ZSH/oh-my-zsh.sh" || return 1',
                'source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh || return 1',
                'source "$HOME/.config/linux-os-setup/proxy.zsh"',
                *runtime_lines,
                'source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh || return 1', 'typeset -g _WORKSTATION_SHELL_LOADED=1', ''])
            add('.config/linux-os-setup/shell.zsh', shell, 'shell-integration')
            for name in ['proxy.zsh', 'proxy-settings.py']:
                add('.config/linux-os-setup/' + name, (root / 'user-files' / name).read_text(), 'shell-integration')
            # Configuration for the shell tools started above. Each is written
            # only when its capability is selected, so a machine that does not
            # install the tool does not get a stray configuration file.
            if 'starship' in selected:
                add('.config/starship.toml',
                    (root / 'user-files/starship.toml').read_text(), 'shell-integration')
            if 'atuin' in selected:
                add('.config/atuin/config.toml',
                    (root / 'user-files/atuin.toml').read_text(), 'shell-integration')
            add('.selected_editor', 'SELECTED_EDITOR="/usr/bin/vim"\n', 'shell-integration')
            add('.zshrc', merge_include(read_owned(home, '.zshrc'), 'source "$HOME/.config/linux-os-setup/shell.zsh"'), 'shell-integration')
    git_lines, git_owners = [], []
    def quote(text):
        return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if 'git-identity' in selected:
        if {'chezmoi', 'git'} <= set(selected) and private.get('identities'):
            for identity in private['identities']:
                relative = '.config/linux-os-setup/git-' + identity['scope'] + '.conf'
                add(relative, '[user]\n\tname = ' + quote(identity['name']) + '\n\temail = ' + quote(identity['email']) + '\n', 'git-identity')
                git_lines += ['[includeIf ' + quote('gitdir:' + identity['directory'].rstrip('/') + '/') + ']', '\tpath = ' + quote(str(home / relative))]
            git_owners.append('git-identity')
        else:
            deferred.append('git-identity')
    if 'git-lfs-filters' in selected:
        if {'chezmoi', 'git', 'git-lfs'} <= set(selected):
            git_lines += ['[filter "lfs"]', '\tclean = git-lfs clean -- %f', '\tsmudge = git-lfs smudge -- %f', '\tprocess = git-lfs filter-process', '\trequired = true']
            git_owners.append('git-lfs-filters')
        else:
            deferred.append('git-lfs-filters')
    if git_lines:
        relative = '.config/linux-os-setup/git.conf'
        merged = merge_include(read_owned(home, '.gitconfig'), '[include]\n\tpath = ' + quote(str(home / relative)))
        for owner in git_owners:
            add(relative, '\n'.join(git_lines) + '\n', owner)
            add('.gitconfig', merged, owner)
    return files, owners, deferred


def verify(home, selected, private, tools):
    try:
        files, owners, deferred = render(home, selected, private, tools)
        checks = [{'id': key, 'status': 'deferred', 'reason': 'missing-user-settings-or-selected-prerequisites'} for key in deferred]
        for key, paths in owners.items():
            passed = all((home / p).is_file() and not (home / p).is_symlink() and (home / p).read_text() == files[p] and not (home / p).stat().st_mode & 0o077 for p in paths)
            checks.append({'id': key, 'status': 'passed' if passed else 'failed', 'reason': 'owned-user-files-match' if passed else 'missing-or-modified-user-files'})
        return checks
    except (InputError, OSError, UnicodeError):
        return [{'id': key, 'status': 'failed', 'reason': 'user-file-conflict-or-unreadable'} for key in sorted(BEHAVIORS & set(selected))]


def apply(config, selected, private, tools):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'user-files-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-user-files')
    home = Path(account.pw_dir)
    files, owners, deferred = render(home, selected, private, tools)
    changed = {p: body for p, body in files.items() if not (home / p).exists() or (home / p).read_text() != body or (home / p).stat().st_mode & 0o077}
    if not changed:
        return False
    tool = tools['chezmoi']
    validate_payload(destination(home, tool), tool)
    state = home / '.local/state/linux-os-setup/user-files'
    safe_path(home, state)
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    state.chmod(0o700)
    with tempfile.TemporaryDirectory(dir=state) as temporary:
        working = Path(temporary)
        source = working / 'source'
        source.mkdir(mode=0o700)
        backup = state / ('backup-' + uuid.uuid4().hex)
        backup.mkdir(mode=0o700)
        manifest = []
        for n, (relative, body) in enumerate(changed.items()):
            target = home / relative
            if target.exists():
                raw = target.read_bytes()
                saved = backup / str(n)
                saved.write_bytes(raw)
                saved.chmod(0o600)
                manifest.append({'path': relative, 'file': str(n), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': target.stat().st_mode & 0o777})
            components = ['dot_' + p[1:] if p.startswith('.') else p for p in Path(relative).parts]
            components[-1] = 'private_' + components[-1]
            output = source.joinpath(*components)
            output.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            output.write_text(body)
            output.chmod(0o600)
        manifest_path = backup / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        manifest_path.chmod(0o600)
        conf = working / 'chezmoi.json'
        conf.write_text('{}\n')
        conf.chmod(0o600)
        environment = {k: v for k, v in os.environ.items() if not k.startswith('CHEZMOI_')}
        command = [str(destination(home, tool) / tool['entrypoint']), '--config', str(conf), '--source', str(source),
                   '--destination', str(home), '--persistent-state', str(working / 'state.boltdb'), '--cache', str(working / 'cache'),
                   '--no-tty', '--no-pager', '--force', 'apply', '--include=files,dirs']
        subprocess.run(command, check=True, capture_output=True, env=environment, timeout=60)
    require(all(c['status'] != 'failed' for c in verify(home, selected, private, tools)), 'user-files-post-apply-drift')
    return True
