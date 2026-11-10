"""Repository baseline contract; uses no third-party packages."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RepositoryBaselineTests(unittest.TestCase):
    def test_repository_has_explicit_python(self):
        version_file = ROOT / '.python-version'
        self.assertTrue(version_file.is_file(), 'Explicit Python version is missing')
        self.assertEqual(version_file.read_text().strip(), '3.12')

    def test_repository_excludes_runtime_and_secrets(self):
        paths = ['.venv/lib/cache', '.venv-probe/lib/cache', '.venv-repro/cache',
                 '.runtime/a0/report.json', '.cache/models/file', '.env',
                 'private.pem', '.worktrees/branch/README.md', 'node_modules/pkg/index.js',
                 'runtime.sqlite', '.superpowers/sdd/ledger.md']
        for path in paths:
            with self.subTest(path=path):
                result = subprocess.run(['git', 'check-ignore', '--no-index', '-q', path],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, f'{path} must be ignored')
        for path in ['src/ontology_platform/semantic/dto.py', 'README.md', '.env.example']:
            with self.subTest(path=path):
                result = subprocess.run(['git', 'check-ignore', '--no-index', '-q', path],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, f'{path} must remain trackable')

    def test_readme_identifies_tool_only_scope(self):
        readme = ROOT / 'README.md'
        self.assertTrue(readme.is_file(), 'README is missing')
        text = readme.read_text()
        self.assertIn('只开发工具', text)
        self.assertIn('Semantica', text)


if __name__ == '__main__':
    unittest.main()
