"""The pre-deployment version report.

Its job is to say what would change before anything is written, and to be
honest about what it cannot refresh: most pins live in hand-curated locks whose
payloads carry per-file digests, and a sweep must not pretend otherwise.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))

SOURCES = json.loads((ROOT / 'catalogue/update-sources.json').read_text())['sources']
REPORT = ROOT / 'script/update-report'


def load_module():
    """Load the script as a module. It resolves its own root from __file__, so
    that has to be supplied."""
    import importlib.util
    spec = importlib.util.spec_from_loader('update_report', loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__dict__['__file__'] = str(REPORT)
    exec(compile(REPORT.read_text(), str(REPORT), 'exec'), module.__dict__)
    return module


class SourceDeclarationTest(unittest.TestCase):
    def test_every_source_names_a_probe(self):
        for source in SOURCES:
            self.assertIn('probe', source, source['id'])

    def test_every_lock_referenced_exists(self):
        for source in SOURCES:
            if 'lock' in source:
                self.assertTrue((ROOT / source['lock']).is_file(),
                                f"{source['id']} names a missing lock")

    def test_every_pinned_lock_is_covered(self):
        """A lock nobody watches silently goes stale."""
        watched = {source.get('lock') for source in SOURCES}
        for lock in sorted((ROOT / 'locks').glob('*.json')):
            if lock.name.endswith('schema.json'):
                continue
            if lock.stem in ('go', 'rust'):
                continue  # dormant by decision, not selected
            self.assertIn(f'locks/{lock.name}', watched,
                          f'{lock.name} is pinned but no update source watches it')

    def test_sources_without_a_feed_say_why(self):
        for source in SOURCES:
            if source['probe'] == 'none':
                self.assertTrue(source.get('note'), f"{source['id']} needs a reason")

    def test_ids_are_unique(self):
        identifiers = [source['id'] for source in SOURCES]
        self.assertEqual(len(identifiers), len(set(identifiers)))


class NormalisationTest(unittest.TestCase):
    """Projects spell the same release many ways."""

    def setUp(self):
        self.module = load_module()

    def test_tag_prefixes_are_ignored(self):
        normalise = self.module.normalise
        self.assertEqual(normalise('v1.2.3'), normalise('1.2.3'))
        self.assertEqual(normalise('rust-v0.154.0'), normalise('0.154.0'))
        self.assertEqual(normalise('mandrel-25.0.4.1-Final'), normalise('25.0.4.1-Final'))
        self.assertEqual(normalise('jdk-25.0.4.1+1'), normalise('25.0.4.1-1'))

    def test_unrelated_versions_still_differ(self):
        normalise = self.module.normalise
        self.assertNotEqual(normalise('v1.2.3'), normalise('v1.2.4'))

    def test_empty_values_are_handled(self):
        self.assertEqual(self.module.normalise(None), '')


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_equal_after_normalising_is_current(self):
        self.assertTrue(self.module.matches('1.18.31', 'v1.18.31', {}))

    def test_containment_match_for_dated_releases(self):
        """python-build-standalone tags by date; the pin embeds that date."""
        self.assertTrue(self.module.matches(
            '3.14.7+20260901', '20260901', {'match': 'contains'}))

    def test_containment_is_not_the_default(self):
        self.assertFalse(self.module.matches('3.14.7+20260901', '20260901', {}))


class RecordedVersionTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_reads_a_list_of_artifacts(self):
        source = next(s for s in SOURCES if s['id'] == 'chezmoi')
        self.assertTrue(self.module.recorded(source))

    def test_reads_a_mapping_of_artifacts(self):
        """bootstrap.json keys its artifacts by id instead of listing them."""
        source = next(s for s in SOURCES if s['id'] == 'controller')
        self.assertTrue(self.module.recorded(source))

    def test_reads_a_top_level_field(self):
        source = next(s for s in SOURCES if s['id'] == 'claude-code')
        self.assertTrue(self.module.recorded(source))

    def test_an_unknown_artifact_is_not_invented(self):
        self.assertIsNone(self.module.recorded(
            {'lock': 'locks/user-tools.json', 'artifact': 'nothing-like-this',
             'probe': 'github_release'}))


class ReportBehaviourTest(unittest.TestCase):
    def run_report(self, *args):
        return subprocess.run([sys.executable, '-B', str(REPORT), *args],
                              capture_output=True, text=True, cwd=ROOT, timeout=900)

    def test_a_report_writes_nothing_and_succeeds(self):
        before = (ROOT / 'manifest/binaries.json').read_bytes()
        result = self.run_report('--only', 'maven')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Nothing was written', result.stdout)
        self.assertEqual((ROOT / 'manifest/binaries.json').read_bytes(), before)

    def test_it_distinguishes_automatic_from_review(self):
        module = load_module()
        automatic = [s for s in SOURCES if s.get('apply')]
        self.assertTrue(automatic, 'some sources must be re-pinnable automatically')
        for source in automatic:
            self.assertTrue(source['apply'].startswith('script/'))

    def test_hand_curated_locks_are_never_marked_automatic(self):
        """Their payloads carry per-file digests; a sweep must not rewrite them."""
        for identifier in ('node', 'mandrel', 'temurin-25', 'cline'):
            source = next(s for s in SOURCES if s['id'] == identifier)
            self.assertIsNone(source.get('apply'),
                              f'{identifier} must not be re-pinned by a sweep')


class ApplyCommandTest(unittest.TestCase):
    """Apply commands are split with shlex, not str.split.

    One carries a quoted licence string; splitting on whitespace turns it into
    three stray arguments and the resolver refuses them.
    """

    def test_a_quoted_argument_survives_splitting(self):
        import shlex
        source = next(s for s in SOURCES if s['id'] == 'claude-code')
        arguments = shlex.split(source['apply'])
        licence = arguments[arguments.index('--licence') + 1]
        self.assertEqual(licence, 'Anthropic commercial terms')
        self.assertNotIn('commercial', arguments[arguments.index('--licence') + 2:])

    def test_naive_splitting_would_break_it(self):
        source = next(s for s in SOURCES if s['id'] == 'claude-code')
        naive = source['apply'].split()
        self.assertNotEqual(naive[naive.index('--licence') + 1],
                            'Anthropic commercial terms',
                            'this is why shlex is used')

    def test_every_apply_command_splits_cleanly(self):
        import shlex
        for source in SOURCES:
            if source.get('apply'):
                arguments = shlex.split(source['apply'])
                self.assertTrue(arguments[0].startswith('script/'))
                self.assertNotIn("'", ' '.join(arguments),
                                 f"{source['id']}: quotes leaked into an argument")


class GitHubAuthenticationTest(unittest.TestCase):
    """Checking every pin needs more than GitHub's 60 unauthenticated requests
    an hour, and a token kept by gh can be stale."""

    def setUp(self):
        self.module = load_module()

    def test_an_environment_token_is_preferred(self):
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'from-environment'}):
            self.assertEqual(self.module.github_token(), 'from-environment')

    def test_gh_supplies_a_token_when_the_environment_does_not(self):
        import subprocess as sp
        with patch.dict('os.environ', {'GITHUB_TOKEN': '', 'GH_TOKEN': ''}), \
             patch.object(self.module.subprocess, 'run',
                          return_value=sp.CompletedProcess([], 0, 'from-gh\n', '')):
            self.assertEqual(self.module.github_token(), 'from-gh')

    def test_a_missing_gh_is_not_an_error(self):
        with patch.dict('os.environ', {'GITHUB_TOKEN': '', 'GH_TOKEN': ''}), \
             patch.object(self.module.subprocess, 'run', side_effect=OSError):
            self.assertIsNone(self.module.github_token())

    def test_a_forbidden_response_retries_without_the_token(self):
        """A stale token must not break the tool: GitHub answers a bad token
        with 403 rather than ignoring it."""
        import urllib.error
        calls = []

        def fake_read(url, token=None):
            calls.append(token)
            if token:
                raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
            return '{"tag_name": "v1.0.0"}'

        with patch.object(self.module, 'github_token', return_value='stale'), \
             patch.object(self.module, 'read', side_effect=fake_read):
            body = self.module.fetch('https://api.github.com/repos/x/y/releases/latest')
        self.assertIn('v1.0.0', body)
        self.assertEqual(calls, ['stale', None], 'it must retry unauthenticated')

    def test_rate_limiting_is_reported_as_such(self):
        import urllib.error

        def always_forbidden(url, token=None):
            raise urllib.error.HTTPError(url, 403, 'rate limit exceeded', {}, None)

        with patch.object(self.module, 'github_token', return_value=None), \
             patch.object(self.module, 'read', side_effect=always_forbidden):
            with self.assertRaises(LookupError):
                self.module.fetch('https://api.github.com/repos/x/y/releases/latest')

    def test_non_github_urls_are_never_authenticated(self):
        calls = []

        def fake_read(url, token=None):
            calls.append(token)
            return 'body'

        with patch.object(self.module, 'github_token', return_value='unused'), \
             patch.object(self.module, 'read', side_effect=fake_read):
            self.module.fetch('https://registry.npmjs.org/cline/latest')
        self.assertEqual(calls, [None])


if __name__ == '__main__':
    unittest.main()
