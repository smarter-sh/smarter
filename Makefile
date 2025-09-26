SHELL := /bin/bash
include .env
export PATH := /usr/local/bin:$(PATH)
export

ifeq ($(OS),Windows_NT)
    PYTHON := python.exe
    ACTIVATE_VENV := venv\Scripts\activate
else
    PYTHON := python3.12
    ACTIVATE_VENV := source venv/bin/activate
endif
PIP := $(PYTHON) -m pip

ifneq ("$(wildcard .env)","")
else
    $(shell cp ./docs/example-dot-env .env)
endif

.PHONY: init activate build run test clean tear-down lint analyze coverage release pre-commit-init pre-commit-run python-init python-activate python-lint python-clean python-test docker-compose-install docker-init docker-build docker-run docker-test python-init python-lint python-clean keen-init keen-build keen-server change-log help

# Default target executed when no arguments are given to make.
all: help

# initialize local development environment.
# takes around 5 minutes to complete
init:
	make check-python		# verify Python 3.11 is installed
	make docker-check		# verify Docker is installed and running
	make python-init		# create/replace Python virtual environment and install dependencies
	make docker-init		# initialize MySQL and create the smarter database
	make pre-commit-init	# install and configure pre-commit

activate:
	./scripts/activate.sh

# complete Docker build. Performs all 13 steps of the build process regardless of current state.
# takes around 4 minutes to complete
build:
	make docker-build

# run the web application from Docker
# takes around 30 seconds to complete
run:
	make docker-run

requirements:
	pip install --upgrade pip setuptools wheel pip-tools
	pip-compile smarter/requirements/in/local.in -o smarter/requirements/local.txt
	pip-compile smarter/requirements/in/docker.in -o smarter/requirements/docker.txt

test:
	make docker-test

clean:
	make python-clean
	make docker-prune

# destroy all Docker build and local artifacts
# takes around 1 minute to complete
tear-down:
	make python-clean
	make docker-prune

# ---------------------------------------------------------
# Code management
# ---------------------------------------------------------

lint:
	make python-lint

analyze:
	cloc . --exclude-ext=svg,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

coverage:
	docker exec smarter-app bash -c "coverage run manage.py test && coverage report -m && coverage html"

pre-commit-init:
	pre-commit install
	pre-commit autoupdate

pre-commit-run:
	pre-commit run --all-files

release:
	git commit -m "fix: force a new release" --allow-empty && git push


# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
docker-check:
	@docker ps >/dev/null 2>&1 || { echo >&2 "This project requires Docker but it's not running.  Aborting."; exit 1; }

docker-shell:
	make docker-check && \
	docker exec -it smarter-app /bin/bash


docker-init:
	@read -p "AWS keypair and OpenAI Api key must be present in your .env file. Continue? [y/N]: " ans; \
		if [ "$$ans" != "y" ] && [ "$$ans" != "Y" ]; then \
			echo "Aborted."; exit 1; \
		fi && \
	make docker-check && \
	make docker-prune && \
	rm -rf ./mysql-data && \
	find ./ -name celerybeat-schedule -type f -exec rm -f {} + && \
	docker system prune -a --volumes && \
	docker volume prune -f && \
	docker network prune -f && \
	images=$$(docker images -q) && [ -n "$$images" ] && docker rmi $$images -f || echo "No images to remove" && \
	echo "Building Docker images..." && \
	docker-compose up -d && \
	echo "Initializing Docker..." && \
	docker exec smarter-mysql bash -c "sleep 20; until echo '\q' | mysql -u smarter -psmarter; do sleep 10; done" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter;' && \
	docker exec smarter-app bash -c "\
		python manage.py makemigrations && python manage.py migrate && \
		python manage.py initialize_waffle && \
		python manage.py create_smarter_admin --username admin --email admin@smarter.sh --password smarter && \
		python manage.py create_user --account_number 3141-5926-5359 --username staff_user --email staff@smarter.sh --password smarter --first_name Smarter --last_name User --admin && \
		python manage.py create_user --account_number 3141-5926-5359 --username customer_user --email customer@smarter.sh --password smarter --first_name Customer --last_name User && \
		python manage.py add_plugin_examples --username admin && \
		python manage.py verify_dns_configuration && \
		python manage.py deploy_example_chatbot && \
		python manage.py seed_chat_history && \
		python manage.py load_from_github --account_number 3141-5926-5359 --username admin --url https://github.com/smarter-sh/smarter-demo && \
		python manage.py load_from_github --account_number 3141-5926-5359 --username admin --url https://github.com/smarter-sh/examples --repo_version 2 && \
		python manage.py initialize_wagtail && \
		python manage.py initialize_providers && \
		python manage.py create_stackacademy_sql_plugin --db_host sql.lawrencemcdaniel.com --db_name smarter_test_db --db_username smarter_test_user && \
		python manage.py apply_manifest --filespec 'smarter/apps/account/data/sample-secrets/smarter-test-db.yaml' --username admin && \
		python manage.py apply_manifest --filespec 'smarter/apps/plugin/data/sample-connections/smarter-test-db.yaml' --username admin && \
		python manage.py apply_manifest --filespec 'smarter/apps/account/data/sample-secrets/smarter-test-db.yaml' --username admin" && \
		python manage.py create_stackademy_sql_chatbot && \
		python manage.py create_stackademy_api_chatbot && \
	echo "Docker and Smarter are initialized." && \
	docker ps

docker-build:
	make docker-check && \
	docker-compose build
	docker image prune -f

docker-run:
	make docker-check && \
	docker-compose up


docker-test:
	make docker-check && \
	docker exec smarter-app bash -c "./manage.py test smarter"

docker-prune:
	make docker-check && \
	docker-compose down && \
	docker builder prune -a -f && \
	docker image prune -a -f

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo >&2 "This project requires $(PYTHON) but it's not installed.  Aborting."; exit 1; }

python-init:
	mkdir -p .pypi_cache && \
	make check-python
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	PIP_CACHE_DIR=.pypi_cache $(PIP) install --upgrade pip && \
	PIP_CACHE_DIR=.pypi_cache $(PIP) install -r smarter/requirements/local.txt

python-lint:
	make check-python
	make pre-commit-run
	pylint smarter/smarter

python-clean:
	rm -rf venv
	find ./smarter/ -name __pycache__ -type d -exec rm -rf {} +

# ---------------------------------------------------------
# Keen
# ---------------------------------------------------------
keen-init:
	cd keen_v3.0.6/tools && npm install --global yarn && \
	npm install gulp@^4.0.2 && \
	npm install gulp-cli && \
	gulp --version

keen-build:
	cd keen_v3.0.6/tools && \
	yarn && \
	gulp --demo1

keen-server:
	cd keen_v3.0.6/tools && \
	gulp localhost


# -------------------------------------------------------------------------
# AWS and deployment
# -------------------------------------------------------------------------
helm-update:
	cd helm/charts/smarter && \
	helm dependency update


change-log:
	@echo "Generating changelog..."
	npx conventional-changelog -p angular -i CHANGELOG.md -s

######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'init                   - Initialize local and Docker environments'
	@echo 'activate               - activates Python virtual environment'
	@echo 'build                  - Build Docker containers'
	@echo 'run                    - run web application from Docker'
	@echo 'test                   - run Python-Django unit tests in Docker'
	@echo 'requirements           - compile and update Python dependency files'
	@echo 'clean                  - delete all local artifacts, virtual environment, node_modules, and Docker containers'
	@echo 'tear-down              - destroy all docker build and local artifacts'
	@echo '<************************** Code Management **************************>'
	@echo 'lint                   - Run all code linters and formatters'
	@echo 'analyze                - Generate code analysis report using cloc'
	@echo 'coverage               - Generate Docker-based code coverage analysis report'
	@echo 'pre-commit-init        - install and configure pre-commit'
	@echo 'pre-commit-run         - runs all pre-commit hooks on all files'
	@echo 'release                - Force a new Github release'
	@echo '<************************** AWS **************************>'
	@echo 'helm-update            - Update Helm chart dependencies'
	@echo '<************************** Python **************************>'
	@echo 'python-init            - Create a Python virtual environment and install dependencies'
	@echo 'python-lint            - Run Python linting using pre-commit'
	@echo 'python-clean           - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo '<************************** Docker **************************>'
	@echo 'docker-init            - Initialize MySQL and create the smarter database'
	@echo 'docker-build           - Build all Docker containers using docker-compose'
	@echo 'docker-run             - Start all Docker containers using docker-compose'
	@echo 'docker-compose-install - Install Docker Compose'
	@echo 'docker-test            - Run Python-Django unit tests in Docker'
	@echo '<************************** Keen **************************>'
	@echo 'keen-init              - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build             - Build Keen app using gulp'
	@echo 'keen-server            - Start local Keen web server using gulp'
	@echo '===================================================================='
	@echo 'change-log             - update CHANGELOG.md file'
