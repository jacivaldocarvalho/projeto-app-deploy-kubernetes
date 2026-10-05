SHELL := /bin/bash
.DEFAULT_GOAL := help
PYTHON ?= .venv/bin/python
export KIND_CLUSTER ?= contact-form
export LOCAL_PORT ?= 8080

.PHONY: help setup check build test kind-up deploy-local deploy-registry status logs access smoke kind-down
help:
	@printf '%s\n' 'setup        Install test dependencies in .venv' 'check        Validate syntax and Kubernetes schemas' 'build        Build integration-test images' 'test         Build images and run automated tests' 'kind-up      Create the dedicated local cluster' 'deploy-local Build/load images and deploy to kind' 'deploy-registry Build/push commit-tagged images and deploy to the current kubectl context/namespace' 'status       Show local workloads and storage' 'logs         Show local PHP logs' 'access       Forward the application to localhost:8080' 'smoke        Test HTTP, persistence and MySQL pod replacement' 'kind-down    Delete local cluster/data (CONFIRM=yes required)'
setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r tests/requirements.txt
check:
	bash -n script.sh scripts/local.sh
	node --check frontend/js.js
	python3 -m py_compile scripts/smoke_local.py
	git diff --check
	$(PYTHON) tests/validate_manifests.py
build:
	docker build -f backend/dockerfile -t application-validation-backend:local .
	docker build -f database/dockerfile -t application-validation-database:local .
test: build
	@for file in index.php conexao.php health.php; do docker run --rm application-validation-backend:local php -l "/var/www/html/$$file" || exit; done
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
kind-up deploy-local status logs access smoke:
	bash scripts/local.sh $@
deploy-registry:
	bash script.sh
kind-down:
	@test "$(CONFIRM)" = yes || { echo 'Deleting the cluster removes its database. Use make kind-down CONFIRM=yes.'; exit 1; }
	CONFIRM="$(CONFIRM)" bash scripts/local.sh kind-down
