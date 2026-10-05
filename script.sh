#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for tool in docker kubectl; do
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

echo 'Building application images...'
docker build -f backend/dockerfile -t jncarvalho/projeto-backend:1.0 .
docker build -f database/dockerfile -t jncarvalho/projeto-database:1.0 .

echo 'Pushing application images...'
docker push jncarvalho/projeto-backend:1.0
docker push jncarvalho/projeto-database:1.0

echo 'Configuring database credentials...'
if ! kubectl get secret application-database >/dev/null 2>&1; then
    kubectl create secret generic application-database --from-env-file=.env
else
    echo 'Secret already exists. Rotate credentials explicitly if needed.'
fi

echo 'Applying Kubernetes resources...'
kubectl apply -f services.yml
kubectl apply -f deployment.yml

echo 'Waiting for application deployments...'
kubectl rollout status deployment/mysql --timeout=180s
kubectl rollout status deployment/php --timeout=180s
