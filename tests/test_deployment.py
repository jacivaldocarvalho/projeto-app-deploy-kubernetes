"""Run the Bash deployment script with simulated external mutations."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "0123456789abcdef0123456789abcdef01234567"
CONFIG = "MYSQL_ROOT_PASSWORD=test-root-only\nMYSQL_DATABASE=meubanco\nMYSQL_USER=application\nMYSQL_PASSWORD=test-app-only\n"
STUB = '''
import json, os, shutil, subprocess, sys
from pathlib import Path
tool = Path(sys.argv[0]).name
command = tool + " " + " ".join(sys.argv[1:])
with open(os.environ["MOCK_LOG"], "a") as log:
    log.write(json.dumps(command) + "\\n")
if os.environ.get("MOCK_FAIL") and command.startswith(os.environ["MOCK_FAIL"]):
    sys.exit(1)
if tool == "git":
    if sys.argv[1] == "status":
        print(" M backend/index.php" if os.environ.get("MOCK_DIRTY") else "", end="")
    if sys.argv[1] == "rev-parse":
        print(os.environ["MOCK_SHA"])
    sys.exit(0)
if command.startswith("kubectl kustomize"):
    sys.exit(subprocess.call([os.environ["ACTUAL_KUBECTL"], *sys.argv[1:]]))
if command.startswith("kubectl get secret"):
    sys.exit(0 if os.environ.get("MOCK_SECRET") == "exists" else 1)
if command.startswith("kubectl apply"):
    shutil.copy(sys.argv[-1], os.environ["MOCK_RENDERED"])
sys.exit(0)
'''


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="application-deployment-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for filename in ("script.sh", "deployment.yml", "services.yml"):
            shutil.copy(ROOT / filename, self.root / filename)
        binary = self.root / "bin"
        binary.mkdir()
        # Use the same Python interpreter as the test environment, not a system package.
        for name in ("docker", "kubectl", "git"):
            file = binary / name
            file.write_text("#!" + sys.executable + "\n" + STUB)
            file.chmod(0o755)
        self.binary = binary

    def run_script(self, config=CONFIG, fail="", secret="missing", dirty=""):
        envfile = self.root / ".env"
        if config is None:
            envfile.unlink(missing_ok=True)
        else:
            envfile.write_text(config)
        log = self.root / "commands"
        log.write_text("")
        rendered = self.root / "rendered.yml"
        rendered.unlink(missing_ok=True)
        env = {**os.environ, "PATH": str(self.binary) + os.pathsep + os.environ["PATH"],
               "MOCK_LOG": str(log), "MOCK_FAIL": fail, "MOCK_SECRET": secret,
               "MOCK_SHA": COMMIT, "MOCK_DIRTY": dirty, "ACTUAL_KUBECTL": shutil.which("kubectl"),
               "MOCK_RENDERED": str(rendered)}
        result = subprocess.run(["bash", str(self.root / "script.sh")], cwd=self.root.parent,
                                env=env, capture_output=True, text=True, timeout=30)
        commands = [json.loads(line) for line in log.read_text().splitlines()]
        for command in commands:
            if command.startswith("kubectl kustomize "):
                self.assertFalse(Path(command.removeprefix("kubectl kustomize ")).exists(), "Temporary render directory was not cleaned")
        return result, commands, rendered.read_text() if rendered.exists() else ""

    def test_invalid_configuration_stops_before_external_commands(self):
        for config in (None, CONFIG.replace("test-app-only", ""),
                       CONFIG.replace("test-root-only", "replace-with-a-password"),
                       CONFIG.replace("MYSQL_USER=application", "MYSQL_USER=root")):
            with self.subTest(config=config):
                result, commands, _ = self.run_script(config=config)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(commands, [])

    def test_dirty_repository_is_rejected(self):
        result, commands, _ = self.run_script(dirty="yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(command.startswith(("docker", "kubectl")) for command in commands))

    def test_failures_prevent_later_mutations(self):
        for failed, forbidden in (("kubectl kustomize", "docker"), ("docker build", "docker push"),
                                  ("docker push", "kubectl get"), ("kubectl create secret", "kubectl apply"),
                                  ("kubectl apply", "kubectl rollout")):
            with self.subTest(stage=failed):
                result, commands, _ = self.run_script(fail=failed)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any(command.startswith(forbidden) for command in commands))

    def test_matching_tags_and_existing_secret_preservation(self):
        for secret in ("missing", "exists"):
            with self.subTest(secret=secret):
                result, commands, rendered = self.run_script(secret=secret)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(sum(c.startswith("kubectl create secret") for c in commands), int(secret == "missing"))
                self.assertEqual(sum(c.startswith("kubectl rollout") for c in commands), 3)
                images = [c["image"] for item in yaml.safe_load_all(rendered) if item["kind"] == "Deployment"
                          for c in item["spec"]["template"]["spec"]["containers"]]
                self.assertCountEqual(images, ["jncarvalho/projeto-backend:" + COMMIT, "jncarvalho/projeto-database:" + COMMIT, "jncarvalho/projeto-frontend:" + COMMIT])
                for image in images:
                    self.assertTrue(any(c.startswith("docker build ") and ("-t " + image + " .") in c for c in commands))
                    self.assertIn("docker push " + image, commands)
                self.assertNotIn("unpublished", rendered)
                self.assertEqual((self.root / "deployment.yml").read_bytes(), (ROOT / "deployment.yml").read_bytes())

    def test_rollout_failure_is_reported(self):
        result, commands, _ = self.run_script(fail="kubectl rollout status deployment/mysql")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c.startswith("kubectl rollout status deployment/php") for c in commands))


if __name__ == "__main__":
    unittest.main()
