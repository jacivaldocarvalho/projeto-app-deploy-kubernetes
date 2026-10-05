#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
cluster="${KIND_CLUSTER:-contact-form}"
[[ "$cluster" =~ ^[a-z][a-z0-9-]*$ ]] || { echo 'Invalid KIND_CLUSTER.' >&2; exit 1; }
state="$PWD/.local/$cluster"
namespace=contact-form
mkdir -p "$state"
chmod 700 "$state"
for tool in kind kubectl docker; do
    command -v "$tool" >/dev/null || { echo "Required tool not found: $tool" >&2; exit 1; }
done
k() { kubectl --kubeconfig "$state/kubeconfig" --context "kind-$cluster" --namespace "$namespace" "$@"; }
require_cluster() {
    [[ -f "$state/kubeconfig" && -f "$state/owned" ]] || { echo 'Run make kind-up first.' >&2; exit 1; }
    k get namespace "$namespace" >/dev/null
}
case "${1:-}" in
kind-up)
    if kind get clusters | grep -Fxq "$cluster"; then
        require_cluster
        echo 'Project cluster already exists.'
        exit 0
    fi
    kind create cluster --name "$cluster" --kubeconfig "$state/kubeconfig" --wait 120s
    touch "$state/owned"
    k create namespace "$namespace"
    ;;
deploy-local)
    require_cluster
    command -v python3 >/dev/null
    if [[ ! -f "$state/database.env" ]]; then
        python3 - "$state/database.env" <<'PY'
import os, secrets, sys
with open(os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
    output.write(f'MYSQL_ROOT_PASSWORD={secrets.token_hex(24)}\nMYSQL_DATABASE=meubanco\nMYSQL_USER=application\nMYSQL_PASSWORD={secrets.token_hex(24)}\n')
PY
    fi
    # A unique tag ensures edited working trees never reuse cached pod images.
    tag="local-$(date +%s)-$RANDOM"
    backend="contact-form-backend:$tag"
    database="contact-form-database:$tag"
    docker build -f backend/dockerfile -t "$backend" .
    docker build -f database/dockerfile -t "$database" .
    kind load docker-image "$backend" "$database" --name "$cluster"
    render="$(mktemp -d)"
    trap 'rm -rf -- "$render"' EXIT
    cp deployment.yml services.yml "$render/"
    cat > "$render/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [deployment.yml, services.yml]
namespace: $namespace
images:
  - name: jncarvalho/projeto-backend
    newName: contact-form-backend
    newTag: "$tag"
  - name: jncarvalho/projeto-database
    newName: contact-form-database
    newTag: "$tag"
EOF
    kubectl kustomize "$render" > "$render/rendered.yml"
    if ! k get secret application-database >/dev/null 2>&1; then
        k create secret generic application-database --from-env-file="$state/database.env"
    fi
    k apply -f "$render/rendered.yml"
    k rollout status deployment/mysql --timeout=600s
    k rollout status deployment/php --timeout=300s
    ;;
status) require_cluster; k get deployments,pods,services,pvc; ;;
logs) require_cluster; k logs deployment/php --tail=100; ;;
access) require_cluster; k port-forward --address 127.0.0.1 service/php "${LOCAL_PORT:-8080}:80"; ;;
smoke)
    require_cluster
    python3 scripts/smoke_local.py "$state/kubeconfig" "kind-$cluster" "$namespace"
    ;;
kind-down)
    [[ "${CONFIRM:-}" = yes ]] || { echo 'Cluster deletion requires CONFIRM=yes.' >&2; exit 1; }
    require_cluster
    kind delete cluster --name "$cluster" --kubeconfig "$state/kubeconfig"
    # Retain credentials and ownership metadata for diagnosis; cluster data is gone.
    ;;
*) echo 'Use make help for supported commands.' >&2; exit 1; ;;
esac
