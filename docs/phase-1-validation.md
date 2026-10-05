# Application deployment baseline

## Build and configuration

Run builds from the repository root:

```sh
docker build -f backend/dockerfile -t jncarvalho/projeto-backend:1.0 .
docker build -f database/dockerfile -t jncarvalho/projeto-database:1.0 .
```

The backend image serves both the form and the POST endpoint on the same origin.
GET `/` or `/index.php` serves the form; POST `/index.php` accepts `nome`,
`email` and `comentario`. Successful submissions retain the existing plain-text
response. Invalid input returns HTTP 422, unsupported methods return HTTP 405,
and persistence failures return HTTP 503 without database error details.
Cross-origin access is not enabled; the bundled form uses the same origin.
PHP errors are logged rather than displayed in HTTP responses.

Copy `.env.example` to `.env` and replace both password placeholders. Keep `.env`
private. The scripts consume this file using `kubectl --from-env-file`, not shell
sourcing. Do not wrap values in shell quotes. The application uses a dedicated
database user, not root. Images do not contain credentials.

The scripts build and push the images, create the Secret if absent and apply
resources to the **current kubectl context and namespace**. Check both before
execution. They require permission to push to `jncarvalho` and a cluster with a
default StorageClass and LoadBalancer support. Image names and the existing six
PHP replicas are preserved in this phase.

## Existing installations

Database initialization variables and `001-schema.sql` apply only to an empty
data directory. Changing a Kubernetes Secret does not create database users or
rotate passwords inside an initialized MySQL database.

Before deploying against an existing PVC, back up the database and explicitly
provision the application user with privileges on `meubanco.mensagens`. Match
its password to the Secret. Do not delete or recreate the PVC to fix credentials.
The PVC now relies on the cluster's default StorageClass for new installations;
do not attempt an immutable StorageClass change on an existing bound PVC.
The schema specifies `utf8mb4` for new installations. Existing tables require
an explicit, backed-up charset migration before supporting four-byte Unicode.

Both scripts preserve an existing Secret. The deployment uses that Secret,
even if local `.env` values differ. Database password rotation must be explicit
and coordinated between MySQL and the Secret.

The MySQL Deployment uses one replica and a Recreate strategy to avoid two
database pods concurrently accessing the same data directory during an update.

## Relevant validation

- PHP syntax checks and JavaScript/Bash syntax checks.
- Kubernetes schema validation before applying resources.
- Image builds and isolated database initialization.
- GET form and static assets; valid POST including an apostrophe in the name.
- Missing fields, invalid email, oversized values and non-string fields.
- Unsupported methods and unavailable database responses.

Do not run the deployment scripts as a local test: they publish images and
modify the selected cluster. Use disposable containers and a disposable database
volume for integration checks.

### Validation performed on 2026-10-04

- Both Docker images built successfully using local test tags.
- Both PHP files passed `php -l` inside the backend image.
- `bash -n script.sh`, `node --check frontend/js.js` and `git diff --check` passed.
- All five resources passed offline validation against the official Kubernetes
  v1.28 OpenAPI schema, including unknown-field rejection and the schema's
  `int-or-string` format handling. Selectors, Secret keys and PVC references
  were also checked.
- Disposable containers passed form/assets, database initialization, exact
  persistence of apostrophes and SQL injection text, Unicode, input limits,
  non-string input, method restrictions and unavailable-database checks.
- Bash deployment control flow passed tests using simulated Docker/kubectl
  commands, including early failure and preservation of an existing Secret.

Integration containers, their temporary in-memory database and their network
were removed after validation. No images were published and no cluster resources
were applied. Cluster validation, browser UI testing and execution of the Windows
batch script were not performed in this environment.

## Remaining limitations

PHP 7.4 and MySQL 5.7 are retained pending the separate runtime migration phase.
The application is a demonstration with no authentication or rate limiting.
IDs retain their original random range and are not unique; schema migration is
outside this phase. Readiness probes, resource limits and CI remain follow-up
work. The frontend still uses externally hosted jQuery, fonts and CSS images.
