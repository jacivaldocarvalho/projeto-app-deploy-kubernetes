#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for tool in docker kubectl git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Required tool not found: $tool" >&2
        exit 1
    fi
done
if [[ ! -f .env ]]; then
    echo 'Copy .env.example to .env and configure database credentials first.' >&2
    exit 1
fi
for variable in MYSQL_ROOT_PASSWORD MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD; do
    if ! grep -Eq "^${variable}=.+$" .env; then
        echo "Missing or empty setting in .env: $variable" >&2
        exit 1
    fi
done
if grep -Eq '^MYSQL_(ROOT_PASSWORD|PASSWORD)=replace-with-' .env; then
    echo 'Replace the example passwords in .env before deployment.' >&2
    exit 1
fi
if grep -Eq '^MYSQL_USER=root$' .env; then
    echo 'MYSQL_USER must be a dedicated application user, not root.' >&2
    exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
    echo 'Commit all repository changes before building a commit-tagged deployment.' >&2
    exit 1
fi
image_tag="$(git rev-parse --verify HEAD)"
backend_image="jncarvalho/projeto-backend:$image_tag"
database_image="jncarvalho/projeto-database:$image_tag"
render_directory="$(mktemp -d)"
trap 'rm -rf -- "$render_directory"' EXIT
cp deployment.yml services.yml "$render_directory/"
cat > "$render_directory/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yml
  - services.yml
images:
  - name: jncarvalho/projeto-backend
    newTag: "$image_tag"
  - name: jncarvalho/projeto-database
    newTag: "$image_tag"
EOF
kubectl kustomize "$render_directory" > "$render_directory/rendered.yml"

echo "Building application images for commit $image_tag..."
docker build -f backend/dockerfile -t "$backend_image" .
docker build -f database/dockerfile -t "$database_image" .

echo 'Pushing application images...'
docker push "$backend_image"
docker push "$database_image"

echo 'Configuring database credentials...'
if ! kubectl get secret application-database >/dev/null 2>&1; then
    kubectl create secret generic application-database --from-env-file=.env
else
    echo 'Secret already exists. Rotate credentials explicitly if needed.'
fi

echo 'Applying Kubernetes resources...'
kubectl apply -f "$render_directory/rendered.yml"

echo 'Waiting for application deployments...'
kubectl rollout status deployment/mysql --timeout=600s
kubectl rollout status deployment/php --timeout=300s
