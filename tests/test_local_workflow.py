"""Verify that local commands cannot accidentally use the default cluster."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/local.sh', self.root / 'scripts/local.sh')
        binary = self.root / 'bin'
        binary.mkdir()
        self.log = self.root / 'commands.jsonl'
        for tool in ('kind', 'kubectl', 'docker'):
            path = binary / tool
            path.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                            'with open(os.environ["COMMAND_LOG"], "a") as output:\n'
                            ' output.write(json.dumps(sys.argv[1:]) + "\\n")\n')
            path.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'],
                                COMMAND_LOG=str(self.log), KIND_CLUSTER='contact-form')

    def run_command(self, action):
        return subprocess.run(['bash', 'scripts/local.sh', action], cwd=self.root,
                              env=self.environment, text=True, capture_output=True, timeout=10)

    def test_unowned_cluster_is_rejected_before_kubectl(self):
        result = self.run_command('status')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_status_always_uses_explicit_context_namespace_and_kubeconfig(self):
        state = self.root / '.local/contact-form'
        state.mkdir(parents=True)
        (state / 'owned').touch()
        (state / 'kubeconfig').touch()
        result = self.run_command('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(commands), 2)
        for command in commands:
            self.assertEqual(command[:6], ['--kubeconfig', str(state / 'kubeconfig'),
                                          '--context', 'kind-contact-form',
                                          '--namespace', 'contact-form'])

    def test_direct_deletion_requires_confirmation(self):
        self.environment.pop('CONFIRM', None)
        result = self.run_command('kind-down')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CONFIRM=yes', result.stderr)
        self.assertFalse(self.log.exists())

    def test_invalid_cluster_name_cannot_escape_local_state_directory(self):
        self.environment['KIND_CLUSTER'] = '../other'
        result = self.run_command('status')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / '.local').exists())
        self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()
