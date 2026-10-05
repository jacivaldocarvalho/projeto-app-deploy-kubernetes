# Local Kubernetes with kind

This workflow builds the current working tree and loads images directly into a
dedicated kind cluster. It never pushes images to a registry. The published-image
deployment scripts remain separate and require a clean, committed working tree.
`make deploy-registry` calls `script.sh` to build and push commit-tagged images,
then applies them to the current kubectl context and namespace. It does not create
a cluster and requires configured `.env` credentials and registry authentication.

## Requirements and commands

Use Linux (including a Linux environment in WSL) with GNU Make, Bash, Python 3,
Docker, kind and kubectl. Native Windows execution is not supported. Docker must be
running. Allow several GiB of free memory and disk space for the node and images.
The cluster uses the node image supplied by your installed kind version. Keep
kubectl compatible with that Kubernetes version; this is a local learning setup.

```sh
make help
make setup
make check
make test
make kind-up
make deploy-local
make status
make smoke
make access
```

`make access` keeps a localhost port-forward running. Open
`http://localhost:8080`, then stop the tunnel with Ctrl+C. Override the port with
`make access LOCAL_PORT=8081`. `make logs` displays recent PHP logs.

The default cluster is `contact-form`, with namespace `contact-form`. Set
`KIND_CLUSTER=another-name` consistently on all commands to use another dedicated
cluster. Cluster names must begin with a lowercase letter and contain only
lowercase letters, digits and hyphens. An existing cluster without this project's
ownership marker is rejected.

Kubeconfig and generated database credentials live in `.local/<cluster>/`, which
is excluded from Git and Docker builds. Commands always pass the dedicated
kubeconfig and context; creating the cluster does not replace your default
kubeconfig. Local credentials are generated automatically, with private file
permissions. Your deployment `.env` is not consumed. Existing database Secrets
are preserved; editing the credential file does not rotate database passwords.

Local image tags are unique for each deployment, including uncommitted edits.
Kustomize uses the source manifests, with temporary image and namespace overrides.
All six PHP replicas and the MySQL resource/probe settings remain in use. The
LoadBalancer Service can have a pending external address; access uses port-forward.
The default StorageClass must provision the 10Gi claim; check `make status` if
deployment cannot become ready. Do not manually apply the unpublished images.

## Smoke test and persistence

`make smoke` starts and cleans up its own localhost tunnel. It verifies the form,
HTTP readiness and submission, checks the stored row and bound PVC, deletes the
local MySQL pod, waits for its replacement, then confirms the message survived
and application readiness recovered. It retains one uniquely marked test message.
It intentionally interrupts the local database briefly; run it against disposable
project data. It does not exercise browser JavaScript or simulate a sustained
database outage, node loss, disaster recovery or production load.

Data survives pod replacement within this cluster. Removing the kind cluster
removes its node containers and database storage. To explicitly delete it:

```sh
make kind-down CONFIRM=yes
```

The ignored credentials and kubeconfig remain for diagnosis. Recreating the cluster
starts a fresh database. This local workflow does not modify a remote cluster.

## Validation record

On 2026-10-04 (America/Belem), the workflow passed on kind 0.20.0, Kubernetes
1.27.3 and kubectl 1.28.0. The MySQL deployment and all six PHP replicas became
ready; the 10Gi PVC was bound through the `standard` StorageClass. HTTP submission,
readiness and persistence after MySQL pod replacement passed. Repeating
`kind-up` reused the project cluster. Deletion without confirmation and an invalid
cluster name were rejected. The 15 existing tests passed through `make test`;
source/rendered schema checks, syntax checks and actionlint passed.
Four additional simulated safety checks passed for explicit kubeconfig/context/
namespace routing, unowned clusters, unsafe names and unconfirmed deletion.
The smoke check also passed with `PYTHONOPTIMIZE=1`. Two regression tests verified
that missing forms and missing stored messages still fail under optimization,
without reporting success, and terminate the temporary tunnel.

These older installed versions were used only for this local validation; this
record is not evidence of support for every Kubernetes version. Schema validation
in CI remains independent of local cluster execution; CI does not create kind.
