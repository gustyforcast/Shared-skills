"""Contract tests for read-only skill/plugin release preflight."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / 'scripts' / 'preflight_release.py'


def run_check(source):
    proc = subprocess.run([sys.executable, str(SCRIPT), str(source)], capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = None
    return proc, data


def write_valid(root: Path):
    (root / 'plugin.json').write_text(json.dumps({
        'name': 'sample-plugin', 'version': '0.1.0',
        'description': 'Sample testing only',
    }), encoding='utf-8')
    (root / 'README.md').write_text('Sample skill.\n', encoding='utf-8')
    (root / 'LICENSE').write_text('Demo: rights supplied solely for this synthetic test.\n', encoding='utf-8')
    skill = root / 'skills' / 'sample-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: sample-skill\ndescription: Use when reviewing synthetic examples.\n---\n\n# Workflow\nReview.\n', encoding='utf-8')
    (skill / 'tests').mkdir()
    (skill / 'tests' / 'pressure-scenarios.md').write_text('# Scenarios\n- Case 1\n', encoding='utf-8')


class PreflightTests(unittest.TestCase):
    def test_clean_candidate_never_receives_automatic_publication_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(data['overall'], 'MANUAL_REVIEW_REQUIRED')
            self.assertIn('CHECK_RIGHTS_PROVENANCE', {x['code'] for x in data['findings']})
            self.assertTrue(data['artifact_sha256'])
            self.assertGreater(data['file_count'], 0)

    def test_missing_licence_blocks_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            (root / 'LICENSE').unlink()
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(data['overall'], 'HOLD_AUTOMATED_FINDINGS')
            self.assertIn('LICENCE_MISSING', {x['code'] for x in data['findings']})

    def test_hardcoded_credential_is_flagged_without_reprinting_secret(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            fake_value = 'TEST_ONLY_NOT_A_REAL_CREDENTIAL_98765'
            (root / 'settings.txt').write_text('API_KEY="' + fake_value + '"\n', encoding='utf-8')
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('POSSIBLE_SECRET', {x['code'] for x in data['findings']})
            self.assertNotIn(fake_value, proc.stdout + proc.stderr)

    def test_mismatched_manifests_block_release(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            compat = root / '.codex-plugin'
            compat.mkdir()
            (compat / 'plugin.json').write_text('{"name": "sample-plugin", "version": "0.2.0"}', encoding='utf-8')
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('VERSION_MISMATCH', {x['code'] for x in data['findings']})

    def test_missing_tests_blocks_behaviour_certification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            (root / 'skills/sample-skill/tests/pressure-scenarios.md').unlink()
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('TEST_ARTIFACTS_MISSING', {x['code'] for x in data['findings']})
            self.assertEqual(data['overall'], 'HOLD_AUTOMATED_FINDINGS')

    def test_unsafe_archive_member_is_rejected_without_extracting(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'candidate.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('candidate/plugin.json', '{"name":"sample-plugin","version":"0.1.0"}')
                z.writestr('candidate/../../external.txt', 'unsafe')
            proc, data = run_check(archive)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(data['overall'], 'HOLD_AUTOMATED_FINDINGS')
            self.assertIn('UNSAFE_ARCHIVE_PATH', {x['code'] for x in data['findings']})
            self.assertFalse((Path(d) / 'external.txt').exists())

    @unittest.skipUnless(hasattr(os, 'symlink'), 'Symlinks not supported')
    def test_symlink_is_reported_not_followed(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as external:
            root = Path(d)
            write_valid(root)
            (Path(external) / 'settings.txt').write_text('API_' + 'KEY="do-not-read"', encoding='utf-8')
            (root / 'external').symlink_to(external, target_is_directory=True)
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('SYMLINK_UNSUPPORTED', {x['code'] for x in data['findings']})
            self.assertNotIn('external/settings.txt', json.dumps(data))

    def test_missing_source_does_not_claim_review(self):
        with tempfile.TemporaryDirectory() as d:
            proc, data = run_check(Path(d) / 'absent')
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(data['overall'], 'BLOCKED_INPUT')

    def test_external_contact_information_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            (root / 'docs.md').write_text('Contact: contributor@example.com\n', encoding='utf-8')
            proc, data = run_check(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('PERSONAL_INFORMATION_REVIEW', {x['code'] for x in data['findings']})

    def test_large_files_still_affect_candidate_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_valid(root)
            p = root / 'attachment.pdf'
            p.write_bytes(b'A' * (2 * 1024 * 1024 + 1))
            first, data_a = run_check(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            p.write_bytes(b'B' * (2 * 1024 * 1024 + 1))
            second, data_b = run_check(root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(data_a['artifact_sha256'], data_b['artifact_sha256'])

    def test_multi_root_archive_is_not_accepted_as_single_plugin(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / 'many.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('plugin-a/plugin.json', '{"name":"plugin-a","version":"0.1.0"}')
                z.writestr('plugin-b/plugin.json', '{"name":"plugin-b","version":"0.1.0"}')
            proc, data = run_check(archive)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(data['overall'], 'HOLD_AUTOMATED_FINDINGS')
            self.assertIn('ARCHIVE_ROOT_INVALID', {x['code'] for x in data['findings']})

    def test_zip_candidate_supported_without_unpacking(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'sample-plugin'
            root.mkdir()
            write_valid(root)
            archive = Path(d) / 'candidate.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for f in root.rglob('*'):
                    if f.is_file():
                        z.write(f, 'sample-plugin/' + f.relative_to(root).as_posix())
            proc, data = run_check(archive)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(data['overall'], 'MANUAL_REVIEW_REQUIRED')
            self.assertIn('CHECK_RIGHTS_PROVENANCE', {x['code'] for x in data['findings']})


if __name__ == '__main__':
    unittest.main()
