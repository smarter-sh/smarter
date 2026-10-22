SHELL := /bin/bash
export PATH := /usr/local/bin:$(PATH)
export

ifeq ($(OS),Windows_NT)
    PYTHON := python.exe
    ACTIVATE_VENV := venv/Scripts/activate
else
    PYTHON := python3.14
    ACTIVATE_VENV := source venv/bin/activate
endif
PIP := $(PYTHON) -m pip

# scaffold .env from .env.example, with a new Fernet key, which encrypts Secrets. Every process
# (smarter-app, the workers, each manage.py call) must share it to decrypt the others' Secrets.
ifeq ("$(wildcard .env)","")
    $(shell cp .env.example .env)
    $(shell echo "SMARTER_FERNET_ENCRYPTION_KEY=$$(openssl rand -base64 32 | tr '+/' '-_')" >> .env)
endif
include .env

# Smarter Chat, the React app of the LLMClient prompt workbench, is a package of the React
# workspace, published to npm as @smarter.sh/ui-chat.
SMARTER_CHAT_DIR := smarter/react/packages/smarter.sh-chat


.PHONY: api-contract chat-contract extension-contract llmtool-list-contract llmclient-deployment-contract llmclient-architecture-contract i18n-messages all init activate collectstatic build run test clean tear-down lint analyze coverage pre-commit-init pre-commit-run release change-log \
	docker-check docker-init docker-shell docker-build docker-run docker-test docker-prune \
	docker-build-for-react \
	python-init python-lint python-clean python-requirements check-python \
	keen-init keen-build keen-server \
	react-install react-build react-build-ci react-test react-lint react-storybook \
	helm-update \
	sphinx-init sphinx-docs sphinx-linkcheck \
	help

# Default target executed when no arguments are given to make.
all: help

# initialize local development environment.
# takes between 5 and 20 minutes to complete
init:
	@echo "==============================================================================="
	@echo "Initializing local development environment. This will verify and set up your"
	@echo "Python virtual environment, install all 3rd-party package requirements,"
	@echo "build the Docker containers, initialize the MariaDB database, and create example users,"
	@echo "prompts and AI resources. This may take up to 20 minutes..."
	@echo "==============================================================================="
	make check-python							# verify Python 3.14 is installed
	make docker-check							# verify Docker is installed and running
	make python-init							# create/replace Python virtual environment and install dependencies
	make react-install							# install npm dependencies for React frontend apps
	make react-build							# build React frontend apps and collect static files
	make collectstatic							# collect static files for the Django admin interface and other components
	make docker-build 			                # build the Smarter containers, including building the React frontend components
	make docker-init							# initialize MariaDB and create the smarter database
	make pre-commit-init						# install and configure pre-commit
	@echo ""
	@echo ""
	@echo "==============================================================================="
	@echo "Initialization complete!"
	@echo ""
	@echo "Run 'source venv/bin/activate' to activate the Python virtual environment."
	@echo "Run 'make run' to start the application."
	@echo "    'make help' to see all available commands."
	@echo ""
	@echo "The web console is served at http://localhost:9357/ with the following credentials:"
	@echo "    Username: admin"
	@echo "    Email: admin@$(or $(SMARTER_ROOT_DOMAIN),example.com)"
	@echo "    Password: smarter"
	@echo ""
	@echo "The database is accessible at localhost:3306 with the following credentials:"
	@echo "    Username: root"
	@echo "    Password: smarter"
	@echo ""
	@echo "Feature switches (django-waffle) are at http://localhost:9357/admin/waffle/switch/"
	@echo "They turn features, middleware and per-app logging on and off at runtime, without"
	@echo "a restart."
	@echo "==============================================================================="

activate:
	./scripts/activate.sh

collectstatic:
	python smarter/manage.py collectstatic --noinput

# complete Docker build. Performs all 13 steps of the build process regardless of current state.
# takes around 4 minutes to complete
build:
	@echo "==============================================================================="
	@echo "Building Docker containers ..."
	@echo "==============================================================================="
	make docker-build

# run the web application from Docker
# takes around 30 seconds to complete
run:
	@echo "==============================================================================="
	@echo "Running Docker containers ..."
	@echo "==============================================================================="
	make docker-run

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
	@echo "==============================================================================="
	@echo "Generating code analysis report using cloc ..."
	@echo "==============================================================================="
	cloc . --exclude-ext=svg,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

# docker exec smarter-app bash -c "coverage run manage.py test smarter.apps.llmtool && coverage report -m && coverage html"
coverage:
	@echo "==============================================================================="
	@echo "Generating code coverage report using Docker and coverage.py ..."
	@echo "==============================================================================="
	docker exec smarter-app bash -c "coverage run --source=smarter manage.py test smarter && coverage report -m && coverage xml"


change-log:
	@echo "==============================================================================="
	@echo "Generating changelog..."
	@echo "==============================================================================="
	npx conventional-changelog -p angular -i changelogs/CHANGELOG.md -s

pre-commit-init:
	@echo "==============================================================================="
	@echo "Installing and configuring pre-commit ..."
	@echo "==============================================================================="
	pre-commit install
	pre-commit autoupdate

pre-commit-run:
	@echo "==============================================================================="
	@echo "Running pre-commit hooks on all files ..."
	@echo "==============================================================================="
	pre-commit run --all-files

release:
	@echo "==============================================================================="
	@echo "Forcing a new semantic release on GitHub by creating an empty commit and pushing to the repository ..."
	@echo "==============================================================================="
	git commit -m "fix: force a new release" --allow-empty && git push


# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
docker-check:
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Docker is installed and running ..."
	@echo "==============================================================================="
	@echo ""
	@docker ps >/dev/null 2>&1 || { echo >&2 "This project requires Docker but it's not running.  Aborting."; exit 1; }

docker-init:
	@echo ""
	@echo "==============================================================================="
	@echo "Initializing Docker environment, including MariaDB database and Smarter application setup. This may take a few minutes..."
	@echo "==============================================================================="
	make docker-check && \
	docker-compose up -d && \
	docker exec smarter-mariadb bash -c "sleep 20; until echo '\q' | mariadb -u smarter -psmarter; do echo 'Waiting for MariaDB to be ready...'; sleep 10; done" && \
	docker exec smarter-mariadb mariadb -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;' && \
	docker exec smarter-app bash -c "\
		python manage.py reset_cache && \
		python manage.py makemigrations && python manage.py migrate && \
		python manage.py initialize_platform" && \
	docker exec smarter-mariadb mariadb -u root -psmarter -e "GRANT ALL PRIVILEGES ON *.* TO 'smarter'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;" && \
	docker exec smarter-mariadb mariadb -u smarter -psmarter -e 'UPDATE smarter.llmclient_llmclient SET deployed = 0;'
	@echo "Docker and Smarter are initialized."
	docker ps


docker-shell:
	make docker-check && \

# An abbreviated build to improve developer workflow efficiency by skipping
# static asset collection (including by not building the React frontend components)
docker-build:
	make docker-check && \
	docker-compose build \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=false && \
	docker image prune -f

# A full build, which collects the static files, including the React apps'.
# Build the React apps first, with `cd smarter/react && npm run build`.
docker-build-for-react:
	make docker-check && \
	docker-compose build  --progress=plain \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=true
	docker image prune -f

docker-run:
	make docker-check && \
	docker compose up

# Note: Tests tagged `infrastructure` use the real Kubernetes cluster and AWS (Route53, ACM),
# and are skipped by default. They are slow: a deploy can wait up to 40 minutes for a
# TLS certificate. To include them, pass the environment variable into the container
# (exporting it on the host has no effect):
#   docker exec -e SMARTER_TEST_INFRASTRUCTURE=true smarter-app bash -c "python manage.py test smarter"
# To run only the infrastructure tests:
#   docker exec smarter-app bash -c "python manage.py test smarter --tag infrastructure"
# See smarter/smarter/lib/unittest/runner.py.
docker-test:
	make docker-check && \
	docker exec smarter-app bash -c "python manage.py test smarter"

docker-prune:
	@echo ""
	@echo "==============================================================================="
	@echo "Pruning Docker images, containers, volumes, and networks. "
	@echo "This will free up drive space by removing all unused Docker objects..."
	@echo "==============================================================================="
	make docker-check && \
	docker-compose down && \
	docker builder prune -a -f && \
	docker image prune -a -f
	rm -rf ./mariadb-data && \
	find ./ -name celerybeat-schedule -type f -exec rm -f {} + && \
	docker system prune -a --volumes && \
	docker volume prune -f && \
	docker network prune -f && \
	images=$$(docker images -q) && [ -n "$$images" ] && docker rmi $$images -f || @echo "No images to remove"

# -------------------------------------------------------------------------
# Helm
# -------------------------------------------------------------------------
helm-update:
	@echo "==============================================================================="
	@echo "Updating Helm chart dependencies for smarter/charts/smarter ..."
	@echo "==============================================================================="
	cd helm/charts/smarter && \
	helm dependency update

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

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python:
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Python $(PYTHON) is installed ..."
	@echo "==============================================================================="
	@echo ""
	@command -v $(PYTHON) >/dev/null 2>&1 || { \
	echo >&2 "This project requires $(PYTHON) but it's not installed.  Aborting."; \
	echo >&2 "python --version output:"; \
	python --version 2>&1; \
	exit 1; \
}

python-init:
	@echo "==============================================================================="
	@echo "Initializing Python virtual environment and installing dependencies. This may take a few minutes..."
	@echo "==============================================================================="
	rm -r -f venv && \
	mkdir -p .pypi_cache && \
	make check-python
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install setuptools wheel pip-tools && \
	PIP_CACHE_DIR=.pypi_cache $(PIP) install -r smarter/requirements/local.txt

python-lint:
	@echo ""
	@echo "==============================================================================="
	@echo "Running Python linting using pre-commit ..."
	@echo "==============================================================================="
	@echo ""
	make check-python
	make pre-commit-run
	pylint smarter/smarter

python-clean:
	@echo ""
	@echo "==============================================================================="
	@echo "Cleaning Python virtual environment and __pycache__ directories ..."
	@echo "==============================================================================="
	@echo ""
	rm -rf venv
	find ./smarter/ -name __pycache__ -type d -exec rm -rf {} +

# FIX NOTE: mcdaniel. the pip version pin temporarily resolves a pip-compile issue.
#           AttributeError: 'PackageFinder' object has no attribute 'allow_all_prereleases'
python-requirements:
	@echo "==============================================================================="
	@echo "Compiling and updating Python dependency files using pip-compile ..."
	@echo "==============================================================================="
	pip install --upgrade setuptools wheel "pip-tools>=7.6.1"
	pip-compile smarter/requirements/in/base.in -o smarter/requirements/base.txt
	pip-compile smarter/requirements/in/local.in -o smarter/requirements/local.txt
	pip-compile smarter/requirements/in/docker.in -o smarter/requirements/docker.txt
	pip-compile smarter/requirements/in/docs.in -o smarter/requirements/docs.txt --no-strip-extras


# ---------------------------------------------------------
# React
# ---------------------------------------------------------
react-install:
	cd smarter/react && npm install --include=dev

react-update:
	cd smarter/react && ncu --workspaces --root -u && npm install

react-build:
	@echo "==============================================================================="
	@echo "Building and collecting React files on local filesystem ..."
	@echo "==============================================================================="
	cd smarter/react && NODE_ENV=production npm run build
	make collectstatic
	make build

react-build-ci:
	cd smarter/react && \
	NODE_ENV=production npm ci --include=dev && \
	NODE_ENV=production npm run build

# Run the unit tests of every React app, with a coverage report in smarter/react/coverage/.
# Each story is rendered as a test too. See smarter/react/README.md. The workbench tests the
# Smarter Chat library that it imports, so the library is built first (build:deps).
react-test:
	cd smarter/react && npm run build:deps && npm run coverage

# Check the formatting, lint and types of every React app, as CI does. The apps type-check
# against the workspace libraries' and Smarter Chat's declarations, which build:deps builds.
react-lint:
	cd smarter/react && npm run build:deps && npm run format:check && npm run lint && npm run typecheck

# Browse a React app's components in Storybook, at http://localhost:6006.
# example: make react-storybook APP=smarter-secret-list
react-storybook:
	cd smarter/react/packages/$(or $(APP),smarter-dashboard) && npm run storybook

# Regenerate the Smarter Chat api contract's JSON Schema and examples from its Pydantic models
# (smarter.apps.prompt.contract.models), in the smarter-app container, and copy the schema into
# Smarter Chat, which generates its TypeScript types from it. Run it after changing the
# models, and commit the changes.
CHAT_CONTRACT_SCHEMA := smarter/apps/prompt/contract/chat-contract.schema.json
CHAT_CONTRACT_EXAMPLE := smarter/apps/prompt/contract/chat-contract.example.json
chat-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_chat_contract_schema"
	docker cp smarter-app:/home/smarter_user/smarter/$(CHAT_CONTRACT_SCHEMA) smarter/$(CHAT_CONTRACT_SCHEMA)
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_chat_contract_example"
	docker cp smarter-app:/home/smarter_user/smarter/$(CHAT_CONTRACT_EXAMPLE) smarter/$(CHAT_CONTRACT_EXAMPLE)
	cp smarter/$(CHAT_CONTRACT_SCHEMA) $(SMARTER_CHAT_DIR)/contract/chat-contract.schema.json
	cd $(SMARTER_CHAT_DIR) && npm run contract:types

# Regenerate the web console's message catalogs, smarter/smarter/locale/<language>/LC_MESSAGES/django.po
# (Django templates and Python) and djangojs.po (the React apps), for every language in settings.LANGUAGES,
# or only LANGUAGE=<code>, and compile them, in the smarter-app container. Translations already in the
# .po files are kept. Run make build first, so that the container has the current templates and code.
I18N_LOCALE_DIR := smarter/locale
i18n-messages:
	cd smarter/react && npm run i18n:extract
	docker cp smarter/react/i18n/messages.js smarter-app:/home/smarter_user/smarter/react/i18n/messages.js
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py update_console_messages $(if $(LANGUAGE),--language $(LANGUAGE),)"
	mkdir -p smarter/$(I18N_LOCALE_DIR)
	docker cp smarter-app:/home/smarter_user/smarter/$(I18N_LOCALE_DIR)/. smarter/$(I18N_LOCALE_DIR)/

# Regenerate the web console's Extensions api contract from its Pydantic models, in the smarter-app
# container, copy it into @smarter/extension-console, and regenerate that package's TypeScript types.
EXTENSION_CONTRACT_SCHEMA := smarter/apps/llmtool/extension/extension-console.schema.json
extension-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_extension_console_schema"
	docker cp smarter-app:/home/smarter_user/smarter/$(EXTENSION_CONTRACT_SCHEMA) smarter/$(EXTENSION_CONTRACT_SCHEMA)
	cp smarter/$(EXTENSION_CONTRACT_SCHEMA) smarter/react/packages/smarter-extension-console/contract/extension-console.schema.json
	cd smarter/react/packages/smarter-extension-console && npm run contract:types

# Regenerate the LLMTool list's Extensions tab api contract from its Pydantic models, in the
# smarter-app container, copy it into @smarter/llmtool-list, and regenerate that package's TypeScript types.
LLMTOOL_LIST_CONTRACT_SCHEMA := smarter/apps/llmtool/views/listview/extension-list.schema.json
llmtool-list-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_extension_list_schema"
	docker cp smarter-app:/home/smarter_user/smarter/$(LLMTOOL_LIST_CONTRACT_SCHEMA) smarter/$(LLMTOOL_LIST_CONTRACT_SCHEMA)
	cp smarter/$(LLMTOOL_LIST_CONTRACT_SCHEMA) smarter/react/packages/smarter-llmtool-list/contract/extension-list.schema.json
	cd smarter/react/packages/smarter-llmtool-list && npm run contract:types

# Regenerate the LLMClient deployment page's contract from its Pydantic models, in the smarter-app
# container, copy it into @smarter/llmclient-deployment, and regenerate that package's TypeScript types.
LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA := smarter/apps/llmclient/views/llmclient-deployment.schema.json
llmclient-deployment-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_llmclient_deployment_schema"
	docker cp smarter-app:/home/smarter_user/smarter/$(LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA) smarter/$(LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA)
	cp smarter/$(LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA) smarter/react/packages/smarter-llmclient-deployment/contract/llmclient-deployment.schema.json
	cd smarter/react/packages/smarter-llmclient-deployment && npm run contract:types

# Regenerate the contract of the workbench's Architecture tab, an LLMClient's tree of SAM resources, from its
# Pydantic models, in the smarter-app container, copy it into @smarter/llmclient-architecture, and regenerate
# that package's TypeScript types.
LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA := smarter/apps/prompt/views/detailviews/llmclient-architecture.schema.json
llmclient-architecture-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_llmclient_architecture_schema"
	docker cp smarter-app:/home/smarter_user/smarter/$(LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA) smarter/$(LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA)
	cp smarter/$(LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA) smarter/react/packages/smarter-llmclient-architecture/contract/llmclient-architecture.schema.json
	cd smarter/react/packages/smarter-llmclient-architecture && npm run contract:types

# Regenerate the Smarter api contract from the platform's Pydantic models, in the smarter-app
# container: the SAM JSON Schemas and examples (one per kind) and the api's OpenAPI document, which the
# smarter cli and the SDKs generate their clients from. Run it after changing a SAM model, the
# journal contract or the cli api, and commit the files.
API_CONTRACT_DIR := smarter/apps/api/v1/contract
api-contract:
	docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py export_api_contract"
	docker cp smarter-app:/home/smarter_user/smarter/$(API_CONTRACT_DIR)/openapi.json smarter/$(API_CONTRACT_DIR)/openapi.json
	rm -f smarter/$(API_CONTRACT_DIR)/sam/*.schema.json
	docker cp smarter-app:/home/smarter_user/smarter/$(API_CONTRACT_DIR)/sam/. smarter/$(API_CONTRACT_DIR)/sam/

# -------------------------------------------------------------------------
# Sphinx Documentation
#
# automated ci-cid build target for Sphinx documentation
# python -m sphinx -T -b html -d _build/doctrees -D language=en . $READTHEDOCS_OUTPUT/html
#
# our local build target for Sphinx documentation is intended to try to match
# what ReadTheDocs does as closely as possible.
# -------------------------------------------------------------------------
sphinx-init:
	@echo ""
	@echo "==============================================================================="
	@echo "Initializing Sphinx documentation environment."
	@echo "Note: this is a simplified Python environment that skips setting up the full"
	@echo "      development environment."
	@echo "==============================================================================="
	make check-python		# verify Python 3.14 is installed
	make python-init		# create/replace Python virtual environment and install dependencies
	make build			    # build the Smarter Docker container
	make pre-commit-init	# install and configure pre-commit

sphinx-docs:
	@echo ""
	@echo "==============================================================================="
	@echo "Building Sphinx documentation using local Python environment."
	@echo "This may take a few minutes..."
	@echo "==============================================================================="
	cd docs && make SPHINXOPTS="-j auto -W -T -D language=en" html

sphinx-linkcheck:
	cd docs && make linkcheck

sphinx-publish:
	cd docs/build/html && \
	aws s3 sync . s3://docs.smarter.sh/ --delete --acl public-read && \
	aws cloudfront create-invalidation --distribution-id E3J3PFZATCQOFX --paths "/*"

######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'init                   - Initialize local and Docker environments'
	@echo 'activate               - Activate Python virtual environment'
	@echo 'build                  - Build Docker containers'
	@echo 'run                    - Run web application from Docker'
	@echo 'test                   - Run Python-Django unit tests in Docker'
	@echo 'clean                  - Delete all local artifacts, virtual environment, node_modules, and Docker containers'
	@echo 'tear-down              - Destroy all Docker build and local artifacts'
	@echo '<************************** Code Management **************************>'
	@echo 'lint                   - Run all code linters and formatters'
	@echo 'analyze                - Generate code analysis report using cloc'
	@echo 'coverage               - Generate Docker-based code coverage report'
	@echo 'pre-commit-init        - Install and configure pre-commit'
	@echo 'pre-commit-run         - Run all pre-commit hooks on all files'
	@echo 'release                - Force a new Github release'
	@echo 'change-log             - Update changelogs/CHANGELOG.md file'
	@echo '<************************** Docker **************************>'
	@echo 'docker-check           - Verify Docker is installed and running'
	@echo 'docker-init            - Initialize MariaDB and create the smarter database'
	@echo 'docker-shell           - Open a shell in the smarter-app Docker container'
	@echo 'docker-build           - Build all Docker containers using docker-compose'
	@echo 'docker-run             - Start all Docker containers using docker-compose'
	@echo 'docker-test            - Run Python-Django unit tests in Docker'
	@echo 'docker-prune           - Remove unused Docker objects and clean up Docker artifacts'
	@echo '<************************** Python **************************>'
	@echo 'check-python           - Verify Python 3.14 is installed'
	@echo 'python-init            - Create a Python virtual environment and install dependencies'
	@echo 'python-lint            - Run Python linting using pre-commit and pylint'
	@echo 'python-clean           - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo 'python-requirements    - Compile and update Python dependency files'
	@echo '<************************** React **************************>'
	@echo 'react-install          - Install npm dependencies for React frontend apps'
	@echo 'react-build            - Build all React frontend apps and collect static files'
	@echo 'react-build-ci         - Build all React frontend apps using CI settings'
	@echo 'react-test             - Run the unit tests of all React apps, with a coverage report'
	@echo 'react-lint             - Check the formatting, lint and types of all React apps'
	@echo 'react-storybook        - Browse a React app in Storybook, e.g. make react-storybook APP=smarter-secret-list'
	@echo 'api-contract           - Regenerate the SAM JSON Schemas and examples, and the api OpenAPI document'
	@echo 'chat-contract          - Regenerate the Smarter Chat api contract schema, and copy it into Smarter Chat'
	@echo 'i18n-messages          - Regenerate and compile the web console translations (.po), optionally LANGUAGE=<code>'
	@echo 'llmclient-architecture-contract - Regenerate the workbench Architecture tab contract schema, and its React types'
	@echo 'llmtool-list-contract  - Regenerate the LLMTool list Extensions tab contract schema, and its React types'
	@echo '<************************** Keen **************************>'
	@echo 'keen-init              - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build             - Build Keen app using gulp'
	@echo 'keen-server            - Start local Keen web server using gulp'
	@echo '<************************** Helm **************************>'
	@echo 'helm-update            - Update Helm chart dependencies'
	@echo '<************************** Sphinx Documentation **************************>'
	@echo 'sphinx-init            - Initialize Sphinx documentation environment'
	@echo 'sphinx-docs            - Build Sphinx documentation'
	@echo 'sphinx-linkcheck       - Check documentation links'
	@echo 'sphinx-publish         - Publish documentation to AWS S3 and invalidate CloudFront cache'
	@echo '===================================================================='
