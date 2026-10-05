"""Smoke checks must reject failures even when Python optimization is enabled."""
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/smoke_local.py'
HARNESS = '''
import runpy, sys
from unittest.mock import Mock, patch
module = runpy.run_path(sys.argv[1])
scenario = sys.argv[2]
sys.argv = ['smoke_local.py', 'unused', 'kind-contact-form', 'contact-form']
process = Mock()
def start(*args, **kwargs):
    kwargs['stdout'].write('Forwarding from 127.0.0.1:12345 -> 80\\n')
    kwargs['stdout'].flush()
    return process
responses = []
def http(url, data=None, **kwargs):
    responses.append((url, data))
    response = Mock(status=200)
    if url.endswith('/health.php'):
        body = b'Ready'
    elif url.endswith('/index.php'):
        body = b'New record created successfully'
    else:
        body = b'<html>Missing form</html>' if scenario == 'form' else b'<form></form>'
    response.read.return_value = body
    context = Mock()
    context.__enter__ = Mock(return_value=response)
    context.__exit__ = Mock(return_value=False)
    return context
with patch('subprocess.Popen', side_effect=start), \\
     patch('urllib.request.urlopen', side_effect=http), \\
     patch('subprocess.check_output', return_value='0') as kubectl:
    try:
        module['main']()
    finally:
        print('requests=' + str(len(responses)))
        print('queries=' + str(kubectl.call_count))
        print('terminated=' + str(process.terminate.called))
'''


class SmokeOptimizationTests(unittest.TestCase):
    def run_scenario(self, scenario):
        return subprocess.run([sys.executable, '-O', '-c', HARNESS, str(SCRIPT), scenario],
                              text=True, capture_output=True, timeout=10)

    def test_missing_form_fails_under_optimization(self):
        result = self.run_scenario('form')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Contact form was not served.', result.stderr)
        self.assertIn('requests=1', result.stdout)
        self.assertIn('terminated=True', result.stdout)
        self.assertNotIn('PASS:', result.stdout)

    def test_missing_row_fails_after_submission_under_optimization(self):
        result = self.run_scenario('row')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Submitted message was not stored.', result.stderr)
        self.assertIn('requests=3', result.stdout)
        self.assertIn('queries=1', result.stdout)
        self.assertIn('terminated=True', result.stdout)
        self.assertNotIn('PASS:', result.stdout)
