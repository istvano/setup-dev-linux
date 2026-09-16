"""Synthetic offline Python/uv project using a locally constructed pure wheel."""
import base64
import csv
import hashlib
from io import StringIO
import os
from pathlib import Path
import subprocess
import zipfile


def make_project(fixture):
    root = fixture / 'python-build'
    root.mkdir()
    wheel = root / 'offline_answer-0.1.0-py3-none-any.whl'
    files = {
        'offline_answer.py': b'def value():\n    return 6 * 7\n',
        'offline_answer-0.1.0.dist-info/METADATA':
            b'Metadata-Version: 2.3\nName: offline-answer\nVersion: 0.1.0\n',
        'offline_answer-0.1.0.dist-info/WHEEL':
            b'Wheel-Version: 1.0\nGenerator: synthetic-stdlib\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
    }
    output = StringIO()
    records = csv.writer(output, lineterminator='\n')
    for name, content in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b'=').decode()
        records.writerow([name, 'sha256=' + digest, len(content)])
    record_path = 'offline_answer-0.1.0.dist-info/RECORD'
    records.writerow([record_path, '', ''])
    with zipfile.ZipFile(wheel, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr(record_path, output.getvalue())
    (root / '.python-version').write_text('3.14.7\n')
    (root / 'pyproject.toml').write_text(
        '[project]\nname = "offline-python-fixture"\nversion = "0.1.0"\n'
        'requires-python = ">=3.14,<3.15"\n'
        'dependencies = ["offline-answer @ file://'+ str(wheel) +'"]\n')
    (root / 'main.py').write_text('from offline_answer import value\nprint(value())\n')
    (root / 'test_answer.py').write_text(
        'import unittest\nfrom offline_answer import value\n'
        'class AnswerTest(unittest.TestCase):\n'
        '    def test_answer(self):\n        self.assertEqual(value(), 42)\n')
    return root


def check(fixture):
    root = make_project(fixture)
    command = r'''
set -e
cd "$1"
uv --version | grep -F 'uv 0.12.13'
python --version | grep -F 'Python 3.14.7'
[[ "$UV_PYTHON_DOWNLOADS" == never ]]
uv python find 3.14.7 --no-config --offline | grep -F '/linux-os-setup/tools/python/3.14.7+20260901/'
uv lock --no-config --offline
uv sync --no-config --offline --locked --no-build
[[ -x .venv/bin/python ]]
[[ "$(./.venv/bin/python -c 'import offline_answer; print(offline_answer.value())')" == 42 ]]
uv run --no-config --offline --locked --no-build python -m unittest -v
[[ "$(uv run --no-config --offline --locked --no-build python main.py)" == 42 ]]
[[ "$(python -c 'import sys; print(sys.version_info[:2])')" == '(3, 14)' ]]
nvm use --silent default
python --version | grep -F 'Python 3.14.7'
'''
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('UV_', 'PYTHON', 'PIP_', 'VIRTUAL_ENV', 'CONDA_'))}
    environment.update(UV_PYTHON_DOWNLOADS='never')
    result = subprocess.run(['zsh', '-i', '-c', command, '--', str(root)],
                            env=environment, capture_output=True, text=True, timeout=180)
    if result.returncode:
        print(result.stdout[-4000:])
        print(result.stderr[-2000:])
        raise AssertionError('Offline Python project fixture failed')
    print('PASS: user Python 3.14.7/uv 0.12.13 local-wheel lock, venv, unittest and run offline')
