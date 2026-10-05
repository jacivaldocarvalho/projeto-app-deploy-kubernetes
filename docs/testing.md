# Testing and continuous integration

## Requirements

Run these checks on Linux with Python 3.12, Node.js 24, Bash, Git, Docker and kubectl
with built-in Kustomize. Docker must be running. Install frontend dependencies and Chromium before the
integration suite (see below). No cluster, registry login,
production credentials or local `.env` is required.

Python packages are test-only dependencies pinned in `tests/requirements.txt`.
Application dependencies remain in the Docker images. Test resources use random
names, an isolated Docker network, a temporary in-memory MySQL data directory and
generated passwords in private temporary files. Container ports bind to localhost.
Normal completion, setup failure and test failure trigger resource cleanup.

## Run locally

From the repository root:

The [Makefile](../Makefile) provides `make setup`, `make check` and `make test`
for these checks. Set `PYTHON=/path/to/venv/bin/python` to reuse another virtualenv.
Real cluster checks are a separate, manual [kind workflow](local-kind.md).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tests/requirements.txt

bash -n script.sh
make frontend-setup
make frontend-browser-setup
make frontend-check
make frontend-test
git diff --check
.venv/bin/python tests/validate_manifests.py

docker build -f backend/dockerfile -t application-validation-backend:local .
docker build -f database/dockerfile -t application-validation-database:local .
docker build -f frontend/dockerfile -t application-validation-frontend:local .
for file in index.php conexao.php health.php; do
  docker run --rm application-validation-backend:local php -l "/var/www/html/$file"
done

.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Validate the workflow with the same pinned linter used in CI:

```sh
docker run --rm -v "$PWD:/repo:ro" --workdir /repo \
  rhysd/actionlint:1.7.11@sha256:6f03470d0152251d7f07f7c4dc019dbe7024c72cd952f839544c7798843efa8f
```

The manifest validator downloads the official Kubernetes v1.35.0 OpenAPI schema,
checks its SHA-256 and caches it in the system temporary directory. It validates
both source manifests and Kustomize output, including unknown fields and
Kubernetes `int-or-string` values. This is an API-schema check, not a cluster
compatibility or scheduling test. Target-cluster validation remains necessary.
For offline execution, set `KUBERNETES_SCHEMA_FILE` to a previously downloaded
copy; its checksum is still verified.

## Test coverage

- `test_application.py`: React shell/assets through Nginx and directly through PHP,
  four Chromium UI checks with database persistence, runtime versions and MySQL
  authentication; exact persistence of apostrophes, SQL injection text and Unicode;
  input boundaries, malformed UTF-8 and non-string fields; HTTP method rules;
  readiness, missing schema, invalid credentials, a stalled database and recovery.
- `test_deployment.py`: Bash execution with simulated Docker/Git/deployment
  commands and real Kustomize rendering; invalid credentials, dirty trees, stage
  failures, matching build/push/apply tags, existing Secrets and temporary cleanup.
- `validate_manifests.py`: source and rendered Kubernetes resources against the
  pinned official schema, without applying resources.
- `test_manifest_validation.py`: rejection of unknown fields and altered schema
  contents, plus correct handling of integer and named ports.
- `test_local_workflow.py`: explicit cluster context, namespace and kubeconfig;
  rejection of unowned clusters, unsafe names and unconfirmed deletion.
- `test_smoke_local.py`: missing form and missing stored message fail even with
  Python optimization enabled; the temporary tunnel is terminated on failure.

Deployment tests never execute real push, Secret creation or kubectl apply.
Integration tests only change their own disposable database.

## GitHub Actions

[Validate application](../.github/workflows/validate.yml) runs on pushes to `main`
and `develop`, pull requests targeting `main` and manual dispatch. It performs the
same schema, three-image builds, TypeScript/component checks, Chromium and
API/deployment tests described above. The job is time-limited
and superseded runs are cancelled.

Official actions are pinned to commit SHAs. The token has `contents: read`, checkout
does not persist credentials and tests do not use repository secrets. Images are
built locally on the runner; there is no image publication or cluster deployment.
The workflow does not use `pull_request_target`.

The badge reports the workflow status on `main`; a newly added workflow has no
successful run until GitHub executes it. Required branch-protection checks must
be configured separately if desired; this phase does not change repository rules.

## Limits

These automated tests do not exercise WSL, browser engines beyond Chromium, actual
Kubernetes probes/scheduling, production workloads or database migration.
Docker- and browser-dependent tests fail if their tools or prebuilt images are missing rather
than being silently skipped. Resource limits are exercised during integration,
but the suite is not a capacity benchmark.

## Initial local validation

On 2026-10-04, all 15 tests passed with the pinned test dependencies. Both images
built successfully; PHP/Bash/JavaScript syntax, actionlint and source/rendered
manifest checks passed. Temporary Docker resources were removed. The GitHub
Actions execution must be confirmed after this workflow is published.
