"""Guard strict schema validation against previously observed manifest errors."""

import contextlib
import copy
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import ValidationError
import yaml

from validate_manifests import ROOT, load_schema, validate


class ManifestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()
        cls.pvc = next(yaml.safe_load_all((ROOT / "deployment.yml").read_text()))
        cls.service = next(yaml.safe_load_all((ROOT / "services.yml").read_text()))

    def validate_resource(self, resource):
        with contextlib.redirect_stdout(io.StringIO()):
            validate([resource], self.schema)

    def test_unknown_fields_are_rejected(self):
        resource = copy.deepcopy(self.pvc)
        resource["spec"]["acessModes"] = ["ReadWriteOnce"]
        with self.assertRaises(ValidationError):
            self.validate_resource(resource)

    def test_integer_or_named_ports_are_supported(self):
        resource = copy.deepcopy(self.service)
        for port in (80, "http"):
            with self.subTest(port=port):
                resource["spec"]["ports"][0]["targetPort"] = port
                self.validate_resource(resource)
        resource["spec"]["ports"][0]["targetPort"] = 80.5
        with self.assertRaises(ValidationError):
            self.validate_resource(resource)

    def test_schema_checksum_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="application-schema-test-") as directory:
            path = Path(directory) / "schema.json"
            path.write_text("{}")
            with patch.dict(os.environ, {"KUBERNETES_SCHEMA_FILE": str(path)}):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    load_schema()


if __name__ == "__main__":
    unittest.main()
