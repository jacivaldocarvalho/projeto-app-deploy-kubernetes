"""Exercise the real PHP/MySQL images using disposable Docker resources."""

import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[1]
BACKEND_IMAGE = "application-validation-backend:local"
DATABASE_IMAGE = "application-validation-database:local"


def docker(*arguments, check=True):
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True, timeout=30)
    if check and result.returncode:
        raise RuntimeError(f"Docker {arguments[0]} failed: {result.stderr}")
    return result


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="application-integration-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.network = "application-validation-" + secrets.token_hex(6)
        cls.database = cls.network + "-db"
        cls.backend = cls.network + "-web"
        cls.root_password = secrets.token_urlsafe(32)
        cls.app_password = secrets.token_urlsafe(32)
        path = Path(cls.temporary.name)
        database_env = path / "database.env"
        database_env.write_text(f"MYSQL_ROOT_PASSWORD={cls.root_password}\nMYSQL_DATABASE=meubanco\nMYSQL_USER=application\nMYSQL_PASSWORD={cls.app_password}\n")
        backend_env = path / "backend.env"
        backend_env.write_text(f"DB_HOST={cls.database}\nDB_NAME=meubanco\nDB_USER=application\nDB_PASSWORD={cls.app_password}\n")
        for file in (database_env, backend_env):
            file.chmod(0o600)
        docker("network", "create", cls.network)
        cls.addClassCleanup(docker, "network", "rm", cls.network)
        docker("run", "-d", "--name", cls.database, "--network", cls.network,
               "--memory", "1g", "--memory-swap", "1g", "--cpus", "1",
               "--tmpfs", "/var/lib/mysql:rw", "--env-file", str(database_env), DATABASE_IMAGE)
        cls.addClassCleanup(docker, "rm", "-f", "-v", cls.database)
        docker("run", "-d", "--name", cls.backend, "--network", cls.network,
               "--memory", "512m", "--memory-swap", "512m", "--cpus", "0.5",
               "--env-file", str(backend_env), "-p", "127.0.0.1::80", BACKEND_IMAGE)
        cls.addClassCleanup(docker, "rm", "-f", "-v", cls.backend)
        port = docker("port", cls.backend, "80/tcp").stdout.strip().rsplit(":", 1)[1]
        cls.base = "http://127.0.0.1:" + port
        deployments = list(yaml.safe_load_all((ROOT / "deployment.yml").read_text()))
        mysql = next(item for item in deployments if item["metadata"]["name"] == "mysql")
        cls.mysql_probe = mysql["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["exec"]["command"]
        cls.wait_ready()

    @classmethod
    def request(cls, path="/index.php", data=None, method=None):
        encoded = urllib.parse.urlencode(data).encode() if data is not None else None
        request = urllib.request.Request(cls.base + path, data=encoded, method=method)
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.status, response.read().decode(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode(), error.headers

    @classmethod
    def wait_ready(cls):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            try:
                if cls.request("/health.php")[:2] == (200, "Ready"):
                    return
            except (OSError, TimeoutError):
                pass
            time.sleep(1)
        raise RuntimeError("Application readiness timed out")

    def query(self, sql):
        code = "require '/var/www/html/conexao.php'; $result=$link->query(" + json.dumps(sql) + "); if ($result instanceof mysqli_result) echo json_encode($result->fetch_all(MYSQLI_ASSOC), JSON_UNESCAPED_UNICODE);"
        result = docker("exec", self.backend, "php", "-r", code).stdout
        return json.loads(result) if result else None

    def setUp(self):
        self.query("DELETE FROM mensagens")
        self.valid = {"nome": "O'Connor", "email": "user@example.com", "comentario": "A valid message"}

    def test_form_assets_and_runtime_versions(self):
        for path in ("/", "/index.php"):
            with self.subTest(path=path):
                status, body, headers = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn("<form", body)
                self.assertNotIn("<?php", body)
                self.assertIn("charset=utf-8", headers["Content-Type"])
        for path in ("/css.css", "/js.js"):
            self.assertEqual(self.request(path)[0], 200)
        self.assertEqual(docker("exec", self.backend, "php", "-r", 'echo PHP_MAJOR_VERSION . "." . PHP_MINOR_VERSION;').stdout, "8.4")
        self.assertIn("8.4.", docker("exec", self.database, "mysql", "--version").stdout)
        command = 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --user=root --batch --skip-column-names --execute="SELECT plugin FROM mysql.user WHERE User=\'application\'"'
        self.assertEqual(docker("exec", self.database, "sh", "-c", command).stdout.strip(), "caching_sha2_password")

    def test_exact_persistence_and_sql_injection(self):
        cases = [self.valid, {**self.valid, "nome": "Robert'); DROP TABLE mensagens; --"},
                 {**self.valid, "nome": "João 🙂", "comentario": "😀" * 100}]
        for data in cases:
            with self.subTest(name=data["nome"]):
                self.assertEqual(self.request(data=data)[:2], (200, "New record created successfully"))
        rows = self.query("SELECT nome, email, comentario FROM mensagens")
        self.assertCountEqual(rows, cases)

    def test_invalid_input_and_boundaries(self):
        cases = [{}, {**self.valid, "nome": ""}, {**self.valid, "nome": " "},
                 {**self.valid, "email": "invalid"}, {**self.valid, "nome": "x" * 51},
                 {**self.valid, "email": "a" * 40 + "@example.com"},
                 {**self.valid, "comentario": "x" * 101}, {**self.valid, "nome": b"\xff"},
                 {"nome[]": "array", "email": self.valid["email"], "comentario": "test"}]
        for index, data in enumerate(cases):
            with self.subTest(case=index):
                self.assertEqual(self.request(data=data)[0], 422)
        self.assertEqual(self.query("SELECT COUNT(*) AS total FROM mensagens")[0]["total"], "0")
        maximum = {**self.valid, "nome": "x" * 50, "comentario": "x" * 100}
        self.assertEqual(self.request(data=maximum)[0], 200)

    def test_method_restrictions(self):
        for method in ("PUT", "DELETE"):
            status, _, headers = self.request(method=method)
            self.assertEqual(status, 405)
            self.assertEqual(headers["Allow"], "GET, POST")
        self.assertEqual(self.request("/health.php", method="POST")[0], 405)

    def test_readiness_and_schema_failure(self):
        self.assertEqual(self.request("/health.php")[:2], (200, "Ready"))
        self.assertEqual(self.request("/health.php")[2]["Cache-Control"], "no-store")
        docker("exec", self.database, *self.mysql_probe)
        self.query("RENAME TABLE mensagens TO readiness_test")
        try:
            self.assertEqual(self.request("/health.php")[:2], (503, "Not ready"))
            self.assertNotEqual(docker("exec", self.database, *self.mysql_probe, check=False).returncode, 0)
        finally:
            self.query("RENAME TABLE readiness_test TO mensagens")
        self.assertEqual(self.request("/health.php")[0], 200)
        self.assertEqual(self.query("SELECT COUNT(*) AS total FROM mensagens")[0]["total"], "0")

    def test_invalid_health_credentials(self):
        code = '$_SERVER["REQUEST_METHOD"]="GET"; include "/var/www/html/health.php"; echo "|" . http_response_code();'
        for value in ("invalid-test-password", ""):
            result = docker("exec", "-e", "DB_PASSWORD=" + value, self.backend, "php", "-r", code)
            self.assertEqual(result.stdout, "Not ready|503")

    def test_unresponsive_database_and_recovery(self):
        docker("pause", self.database)
        try:
            started = time.monotonic()
            self.assertEqual(self.request("/health.php")[:2], (503, "Not ready"))
            self.assertLess(time.monotonic() - started, 8)
            self.assertEqual(self.request("/")[0], 200)
            status, body, _ = self.request(data=self.valid)
            self.assertEqual(status, 503)
            self.assertEqual(body, "Unable to save the message. Please try again later.")
            for secret in (self.root_password, self.app_password):
                self.assertNotIn(secret, body)
        finally:
            docker("unpause", self.database)
        self.wait_ready()
        self.assertEqual(self.query("SELECT COUNT(*) AS total FROM mensagens")[0]["total"], "0")


if __name__ == "__main__":
    unittest.main()
