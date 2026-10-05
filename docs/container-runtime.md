# Container runtime and deployment

## Runtime versions

The backend uses PHP 8.4 with Apache on Debian Bookworm. The database uses
MySQL 8.4 LTS. Both base images are pinned by digest in their Dockerfiles.
Updating a digest is an explicit dependency update: rebuild and run integration
checks before committing it. The tag identifies the version family; the digest
selects its exact image contents.

The only installed PHP extension is `mysqli`. Database credentials remain
runtime configuration; they are not embedded in either image.

## Build and deployment

The registry deployment script requires Docker, Git and kubectl with built-in Kustomize support.
They use the full Git commit hash as the tag for both application images and
refuse to deploy a repository with modified or untracked files. Ignored `.env`
configuration does not make the repository dirty.

For local builds only, use:

```sh
docker build -f backend/dockerfile -t projeto-backend:local .
docker build -f database/dockerfile -t projeto-database:local .
```

Before an actual deployment:

1. Copy `.env.example` to `.env` and replace both password placeholders.
2. Confirm registry access to `jncarvalho` and the kubectl context/namespace.
3. Confirm that the cluster has a default StorageClass and LoadBalancer support.
4. Commit the application changes and ensure the working tree is clean.
5. Run `make deploy-registry` on Linux/WSL, or call `bash script.sh` directly.

The Bash script copies the manifests to an owned temporary directory, renders the image
tags with `kubectl kustomize`, builds and pushes both images, creates the Secret only
if absent, applies the rendered resources and waits for the deployments. It cleans
up temporary files on normal completion or command failure.

The source manifest deliberately uses the `unpublished` tag. Do not apply it
directly; the script replaces this tag with the commit hash before application.
Rendering does not modify tracked files. Changed commits change the Pod template
image reference and trigger a rollout; rebuilding the same commit does not
trigger a new rollout automatically. Do not overwrite an already-published
commit tag with different image contents.

The script preserves an existing Secret. Its values, rather than a changed
local `.env`, remain authoritative for a subsequent deployment. Password changes
must be coordinated with the running database.

## Availability checks

- MySQL startup checks the TCP listener, allowing up to five minutes for
  initialization. Readiness authenticates as the application user over TCP and
  queries the `mensagens` table. The TCP startup probe alone does not establish
  database readiness.
- PHP startup and liveness request `/`, exercising Apache and PHP without a
  database dependency. Readiness requests `/health.php`, which authenticates and
  reads the application table. It returns HTTP 200 (`Ready`) or 503 (`Not ready`)
  and never inserts records or returns credentials. Only GET is accepted.
- Database connect and read timeouts are three seconds each. The PHP readiness
  probe allows eight seconds for these checks.
- A database outage makes PHP unready while PHP liveness can remain successful.
  This avoids restarting healthy application processes because a dependency is
  down. No MySQL liveness probe is configured in this phase.

## Resource configuration

| Container | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| PHP (each of six replicas) | 100m / 500m | 128Mi / 512Mi |
| MySQL (one replica) | 100m / 1000m | 512Mi / 1Gi |

These are starting values for the demonstration, not load-tested sizing. Total
requests are 700m CPU and 1280Mi memory, excluding system components and any
temporary rolling-update surge. Measure real workloads before adjusting them.
The tests use the configured container limits but do not establish production
capacity.

## Persistence and rollback

New installations initialize MySQL 8.4 in the `mysql` subdirectory of the PVC.
This avoids filesystem entries such as `lost+found` in the MySQL data directory.
The Deployment keeps one replica with a Recreate strategy.

This phase targets a fresh installation; no existing database was migrated.
An old MySQL 5.7 data directory must not be mounted directly into MySQL 8.4.
For an existing deployment, plan backup, the supported 5.7 → 8.0 → 8.4 upgrade
path and restore testing separately. See the
[official upgrade paths](https://dev.mysql.com/doc/refman/8.4/en/upgrade-paths.html).
Changing the volume subdirectory does not migrate existing data.

Before updating an installation containing data, back it up and test restoration
on a separate volume. Do not delete the PVC or reuse an initialized MySQL 8.4
directory with an older database version as a rollback procedure.

For application-only rollback, use a previously published backend commit tag
compatible with the current schema and credentials. Database rollback requires
an appropriate backup/restore plan, not just an older image tag.

## Phase 2 validation

Local validation on 2026-10-04 passed:

- Builds using both pinned base images and PHP syntax checks for all three PHP
  files; Bash/JavaScript syntax and Git whitespace checks.
- Offline official Kubernetes v1.28 schema validation of all five source
  resources and their Kustomize-rendered equivalents.
- Fresh MySQL initialization with the configured container CPU/memory limits,
  PHP 8.4 connectivity and the default `caching_sha2_password` authentication.
- Form/assets, exact persistence, SQL injection text, Unicode, input boundaries
  and unsupported HTTP methods.
- Both readiness checks, missing schema, invalid/empty credentials and recovery.
  Health checks did not insert records.
- A paused database produced bounded readiness failure while PHP liveness
  remained available; a stopped database produced generic HTTP 503 responses.
- Bash control flow tests with simulated deployment commands and real Kustomize
  rendering: matching commit tags, dirty-tree rejection, existing Secret
  preservation, interruption after failures and temporary-directory cleanup.

Disposable containers, their database data and their network were removed.
No existing database was migrated, no images were pushed and no cluster was
modified. The Windows batch script was reviewed but not executed during this phase;
native Windows support has since been removed in favor of Linux/WSL. Browser
interaction, cluster scheduling/probe execution and load tests were not performed.
