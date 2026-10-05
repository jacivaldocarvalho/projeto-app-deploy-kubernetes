"""Validate source and rendered resources against a pinned official OpenAPI schema."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

from jsonschema import Draft4Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4
import yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.35.0"
CHECKSUM = "483500149ee52ce5753d75f5639101d985bb4f5e902cc05b1ba7627465d62446"
SCHEMA_URL = f"https://raw.githubusercontent.com/kubernetes/kubernetes/v{VERSION}/api/openapi-spec/swagger.json"
SCHEMA_URI = f"urn:kubernetes:{VERSION}"


def normalize(value):
    if isinstance(value, dict):
        if value.get("format") == "int-or-string":
            value["type"] = ["integer", "string"]
        if value.get("type") == "object" and "properties" in value:
            value["additionalProperties"] = False
        for child in value.values():
            normalize(child)
    elif isinstance(value, list):
        for child in value:
            normalize(child)


def load_schema():
    configured = os.environ.get("KUBERNETES_SCHEMA_FILE")
    path = Path(configured) if configured else Path(tempfile.gettempdir()) / f"application-kubernetes-{VERSION}-{CHECKSUM}.json"
    if not path.exists():
        if configured:
            raise FileNotFoundError(path)
        with urllib.request.urlopen(SCHEMA_URL, timeout=30) as response:
            contents = response.read()
        if hashlib.sha256(contents).hexdigest() != CHECKSUM:
            raise ValueError("Kubernetes schema checksum mismatch")
        path.write_bytes(contents)
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != CHECKSUM:
        raise ValueError("Kubernetes schema checksum mismatch")
    schema = json.loads(contents)
    normalize(schema)
    return schema


def validate(documents, schema):
    registry = Registry().with_resource(SCHEMA_URI, Resource.from_contents(schema, default_specification=DRAFT4))
    for document in documents:
        group, separator, version = document["apiVersion"].partition("/")
        if not separator:
            group, version = "", group
        gvk = {"group": group, "version": version, "kind": document["kind"]}
        definition = next(name for name, value in schema["definitions"].items() if gvk in value.get("x-kubernetes-group-version-kind", []))
        reference = {"$ref": f"{SCHEMA_URI}#/definitions/{definition}"}
        Draft4Validator(reference, registry=registry).validate(document)
        print(f"PASS {document['kind']}/{document['metadata']['name']}")


def main():
    schema = load_schema()
    print(f"Source manifests: official Kubernetes v{VERSION} schema")
    for filename in ("deployment.yml", "services.yml"):
        validate(yaml.safe_load_all((ROOT / filename).read_text()), schema)
    with tempfile.TemporaryDirectory(prefix="application-manifests-") as directory:
        path = Path(directory)
        for filename in ("deployment.yml", "services.yml"):
            shutil.copy(ROOT / filename, path / filename)
        tag = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        config = {"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization", "resources": ["deployment.yml", "services.yml"], "images": [{"name": name, "newTag": tag} for name in ("jncarvalho/projeto-backend", "jncarvalho/projeto-database", "jncarvalho/projeto-frontend")]}
        (path / "kustomization.yaml").write_text(yaml.safe_dump(config))
        rendered = subprocess.check_output(["kubectl", "kustomize", str(path)], text=True)
        print("Rendered manifests:")
        validate(yaml.safe_load_all(rendered), schema)


if __name__ == "__main__":
    main()
