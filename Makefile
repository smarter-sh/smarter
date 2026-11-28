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
# (smarter-api, the workers, each manage.py call) must share it to decrypt the others' Secrets.
ifeq ("$(wildcard .env)","")
    $(shell cp .env.example .env)
    $(shell echo "SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY=$$(openssl rand -base64 32 | tr '+/' '-_')" >> .env)
endif
include .env

# Smarter Chat, the React app of the LLMClient prompt workbench, is a package of the React
# workspace, published to npm as @smarter.sh/ui-chat.


.PHONY: api-contract chart-credentials chat-contract extension-contract llmtool-list-contract llmclient-deployment-contract llmclient-architecture-contract console-session-contract i18n-messages all init activate collectstatic build run test clean tear-down lint analyze coverage pre-commit-init pre-commit-run release change-log \
	terraform-init terraform-plan terraform-apply \
	docker-check docker-init docker-shell docker-build docker-run docker-test docker-prune \
	docker-build-for-react \
	python-init python-lint python-clean python-requirements python-hashes python-cooldown python-audit check-python \
	keen-init keen-build keen-server \
	console console-local \
	helm-update redis-chart-check \
	sphinx-init sphinx-docs sphinx-linkcheck \
	help

# A bare `make` prints the menu of commands. Each target's description is the `## `
# comment after the colon on the target's own line, e.g. `build: ## Build Docker containers`.
.DEFAULT_GOAL := help

all: help

# initialize local development environment.
# takes between 5 and 20 minutes to complete
init: ## Initialize local and Docker environments
	@echo "==============================================================================="
	@echo "Initializing local development environment. This will verify and set up your"
	@echo "Python virtual environment, install all 3rd-party package requirements,"
	@echo "build the Docker containers, initialize the MariaDB database, and create example users,"
	@echo "prompts and AI resources. This may take up to 20 minutes..."
	@echo "==============================================================================="
	make check-python							# verify Python 3.14 is installed
	make docker-check							# verify Docker is installed and running
	make python-init							# create/replace Python virtual environment and install dependencies
	make console								# the web console's pinned release, into smarter/smarter/static/react/
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
	@echo "    Email: admin@$(or $(SMARTER_PLATFORM_ROOT_DOMAIN),example.com)"
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

activate: ## Activate Python virtual environment
	./scripts/activate.sh

collectstatic: ## Collect static files, including the web console's, into smarter/staticfiles/
	python smarter/manage.py collectstatic --noinput

# complete Docker build. Performs all 13 steps of the build process regardless of current state.
# takes around 4 minutes to complete
build: ## Build Docker containers
	@echo "==============================================================================="
	@echo "Building Docker containers ..."
	@echo "==============================================================================="
	make docker-build

# run the web application from Docker
# takes around 30 seconds to complete
run: ## Run web application from Docker
	@echo "==============================================================================="
	@echo "Running Docker containers ..."
	@echo "==============================================================================="
	make docker-run

test: ## Run Python-Django unit tests in Docker
	make docker-test

clean: ## Delete all local artifacts, virtual environment, node_modules, and Docker containers
	make python-clean
	make docker-prune

# destroy all Docker build and local artifacts
# takes around 1 minute to complete
tear-down: ## Destroy all Docker build and local artifacts
	make python-clean
	make docker-prune

# ---------------------------------------------------------
# Code management
# ---------------------------------------------------------

lint: ## Run all code linters and formatters
	make python-lint

analyze: ## Generate code analysis report using cloc
	@echo "==============================================================================="
	@echo "Generating code analysis report using cloc ..."
	@echo "==============================================================================="
	cloc . --exclude-ext=svg,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

# docker exec smarter-api bash -c "coverage run manage.py test smarter.apps.llmtool && coverage report -m && coverage html"
# Celery Beat is stopped while the tests run: its scheduled tasks would change the rows of
# running tests.
coverage: ## Generate Docker-based code coverage report
	@echo "==============================================================================="
	@echo "Generating code coverage report using Docker and coverage.py ..."
	@echo "==============================================================================="
	docker stop smarter-beat > /dev/null || true
	docker exec smarter-api bash -c "coverage run --source=smarter manage.py test smarter && coverage report -m && coverage xml"; status=$$?; \
	docker start smarter-beat > /dev/null; \
	exit $$status


change-log: ## Update changelogs/CHANGELOG.md file
	@echo "==============================================================================="
	@echo "Generating changelog..."
	@echo "==============================================================================="
	npx conventional-changelog -p angular -i changelogs/CHANGELOG.md -s

pre-commit-init: ## Install and configure pre-commit
	@echo "==============================================================================="
	@echo "Installing and configuring pre-commit ..."
	@echo "==============================================================================="
	pre-commit install
	pre-commit autoupdate

pre-commit-run: ## Run all pre-commit hooks on all files
	@echo "==============================================================================="
	@echo "Running pre-commit hooks on all files ..."
	@echo "==============================================================================="
	pre-commit run --all-files

release: ## Force a new Github release
	@echo "==============================================================================="
	@echo "Forcing a new semantic release on GitHub by creating an empty commit and pushing to the repository ..."
	@echo "==============================================================================="
	git commit -m "fix: force a new release" --allow-empty && git push


# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
docker-check: ## Verify Docker is installed and running
	@echo ""
	@echo "==============================================================================="
	@echo "Verifying that Docker is installed and running ..."
	@echo "==============================================================================="
	@echo ""
	@docker ps >/dev/null 2>&1 || { echo >&2 "This project requires Docker but it's not running.  Aborting."; exit 1; }

docker-init: ## Initialize MariaDB and create the smarter database
	@echo ""
	@echo "==============================================================================="
	@echo "Initializing Docker environment, including MariaDB database and Smarter application setup. This may take a few minutes..."
	@echo "==============================================================================="
	make docker-check && \
	docker-compose up -d && \
	docker exec smarter-mariadb bash -c "sleep 20; until echo '\q' | mariadb -u smarter -psmarter; do echo 'Waiting for MariaDB to be ready...'; sleep 10; done" && \
	docker exec smarter-mariadb mariadb -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;' && \
	docker exec smarter-api bash -c "\
		python manage.py reset_cache && \
		python manage.py migrate && \
		python manage.py initialize_platform" && \
	docker exec smarter-mariadb mariadb -u root -psmarter -e "GRANT ALL PRIVILEGES ON *.* TO 'smarter'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;" && \
	docker exec smarter-mariadb mariadb -u smarter -psmarter -e 'UPDATE smarter.llmclient_llmclient SET deployed = 0;'
	@echo "Docker and Smarter are initialized."
	docker ps


docker-shell: ## Open a shell in the smarter-api Docker container
	make docker-check && \

# An abbreviated build to improve developer workflow efficiency by skipping
# static asset collection (including by not building the React frontend components)
docker-build: ## Build all Docker containers using docker-compose
	make docker-check && \
	docker-compose build \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=false && \
	docker image prune -f

# A full build, which collects the static files, including the web console's.
# Install the web console first, with make console.
docker-build-for-react: ## Build all Docker containers, collecting static files (run make console first)
	make docker-check && \
	docker-compose build  --progress=plain \
	  --build-arg DOCKER_COLLECT_STATIC_FILES=true
	docker image prune -f

docker-run: ## Start all Docker containers using docker-compose
	make docker-check && \
	docker compose up

# The Python tests, in shards, as CI splits them: each shard runs in a Docker stack of its own
# (docker-compose.shard.yml), with a copy of the local database, all at once. The tests can't
# share one stack: they write rows without rollback, and share Redis, the dev server and the
# workers. The stacks have no Celery Beat, whose scheduled tasks would change a running test's
# rows. They run the smarter image, not the dev containers, so this builds it first. Without
# SHARDS, the script runs as many shards as Docker's CPUs and memory have room for, about 3.75 GB
# and one CPU each. LABELS runs part of the suite, in one shard unless SHARDS says otherwise, e.g.
#   make docker-test LABELS=smarter.apps.account.tests.test_activation
# Logs go to .test-shards/. Needs smarter-mariadb running, whose database the
# shards copy. See scripts/run_test_shards.py.
#
# Tests tagged `infrastructure` use the real Kubernetes cluster and AWS (Route53, ACM), and are
# skipped. They are slow: a deploy can wait up to 40 minutes for a TLS certificate. Run them
# only when asked, in the dev container, with Celery Beat stopped:
#   docker exec smarter-api bash -c "python manage.py test smarter --tag infrastructure"
# See smarter/smarter/lib/unittest/runner.py.
SHARDS ?=
LABELS ?=
docker-test: ## Run the Python-Django unit tests in Docker, in shards (SHARDS=<n>, LABELS=<dotted paths>)
	make docker-check
	make build
	python3 -I scripts/run_test_shards.py $(if $(SHARDS),--shards $(SHARDS)) $(if $(LABELS),--labels $(LABELS))

docker-prune: ## Remove unused Docker objects and clean up Docker artifacts
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
helm-update: ## Update Helm chart dependencies
	@echo "==============================================================================="
	@echo "Updating Helm chart dependencies for smarter/charts/smarter ..."
	@echo "==============================================================================="
	cd helm/charts/smarter && \
	helm dependency update

# Start the chart's Redis the way its pod starts it, from the rendered chart and the image it pins, and check
# its ACL users. Run it before a change to the chart's Redis or its image: docker-compose and helm template
# can't show what kept prod's Redis from starting on 2026-11-27. Needs helm, docker and the network.
redis-chart-check: ## Start the Helm chart's Redis as its pod does, and check its ACL users
	python3 -I scripts/check_redis_chart.py

# ---------------------------------------------------------
# Keen
# ---------------------------------------------------------
keen-init: ## Install gulp, yarn and dependencies for Keen
	cd keen_v3.0.6/tools && npm install --global yarn && \
	npm install gulp@^4.0.2 && \
	npm install gulp-cli && \
	gulp --version

keen-build: ## Build Keen app using gulp
	cd keen_v3.0.6/tools && \
	yarn && \
	gulp --demo1

keen-server: ## Start local Keen web server using gulp
	cd keen_v3.0.6/tools && \
	gulp localhost

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python: ## Verify Python 3.14 is installed
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

python-init: ## Create a Python virtual environment and install dependencies
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

python-lint: ## Run Python linting using pre-commit and pylint
	@echo ""
	@echo "==============================================================================="
	@echo "Running Python linting using pre-commit ..."
	@echo "==============================================================================="
	@echo ""
	make check-python
	make pre-commit-run
	pylint smarter/smarter

python-clean: ## Destroy the Python virtual environment and remove __pycache__ directories
	@echo ""
	@echo "==============================================================================="
	@echo "Cleaning Python virtual environment and __pycache__ directories ..."
	@echo "==============================================================================="
	@echo ""
	rm -rf venv
	find ./smarter/ -name __pycache__ -type d -exec rm -rf {} +

# FIX NOTE: mcdaniel. the pip version pin temporarily resolves a pip-compile issue.
#           AttributeError: 'PackageFinder' object has no attribute 'allow_all_prereleases'
#
# --allow-unsafe pins pip and setuptools too: the Docker build installs the
# lockfiles with --require-hashes, which refuses any dependency without a hash.
# The hashes are added by python-hashes, not by pip-compile --generate-hashes,
# which took over ten minutes a lockfile (scripts/python_lockfiles.py says why).
python-requirements: ## Compile and update Python dependency files
	@echo "==============================================================================="
	@echo "Compiling and updating Python dependency files using pip-compile ..."
	@echo "==============================================================================="
	pip install --upgrade setuptools wheel "pip-tools>=7.6.1"
	pip-compile --allow-unsafe smarter/requirements/in/base.in -o smarter/requirements/base.txt
	pip-compile --allow-unsafe smarter/requirements/in/local.in -o smarter/requirements/local.txt
	pip-compile --allow-unsafe smarter/requirements/in/docker.in -o smarter/requirements/docker.txt
	pip-compile --allow-unsafe smarter/requirements/in/docs.in -o smarter/requirements/docs.txt --no-strip-extras
	$(MAKE) python-hashes
	$(MAKE) python-cooldown

# The hashes: the sha256 of each pin's wheels and sdist, from PyPI's JSON API, in
# pip-compile's format. The Docker build installs with --require-hashes.
python-hashes: ## Add each pin's hashes to the Python lockfiles
	python3 -I scripts/python_lockfiles.py hash

# The cooldown: fail when a lockfile pins a release uploaded to PyPI in the last
# PYTHON_COOLDOWN_DAYS days, the wait of .github/dependabot.yml. Most malicious
# releases are found and removed within days. The project's own packages are
# exempt (scripts/python_lockfiles.py). A security fix that can't wait:
#   make python-requirements PYTHON_COOLDOWN_ALLOW="package other-package"
# See docs/source/smarter-platform/system-administration/security/supply-chain.rst.
PYTHON_COOLDOWN_DAYS ?= 14
PYTHON_COOLDOWN_ALLOW ?=
python-cooldown: ## Fail when a Python lockfile pins a release uploaded in the last 14 days
	python3 -I scripts/python_lockfiles.py cooldown --days $(PYTHON_COOLDOWN_DAYS) $(foreach package,$(PYTHON_COOLDOWN_ALLOW),--allow $(package))

# The advisory check: fail when a Python lockfile pins a release with a published
# vulnerability (PyPI's and OSV's advisories). The Tests workflow runs it on every
# pull request to main. An advisory that doesn't reach Smarter is ignored below,
# by its id, with the reason; remove the line once the package is upgraded past it.
# See docs/source/smarter-platform/system-administration/security/supply-chain.rst.
PIP_AUDIT_VERSION := 2.10.1
PIP_AUDIT_LOCKFILES := docker local docs
#   langchain: path traversal in the filesystem prompt and chain loaders and the file-search
#   middleware, which Smarter never imports. Held at 1.2.x by in/constraints.in.
PIP_AUDIT_IGNORE += PYSEC-2026-2192
#   langgraph-sdk: the actions= argument of the @auth.on.* decorators of a LangGraph server,
#   which Smarter doesn't run. A dependency of langchain.
PIP_AUDIT_IGNORE += PYSEC-2026-4240
#   mariadb: SQL injection in MariaDB Connector/C through mysql_real_escape_string() with the
#   big5 character set. Smarter's connections are utf8mb4 (settings DATABASES), and use the ORM.
PIP_AUDIT_IGNORE += PYSEC-2026-217
#   social-auth-core: the OpenID Connect nonce isn't bound to the browser's session. Smarter's
#   only OIDC backend, LinkedinOpenIdConnect, is off by default, and replaces the base class's
#   validate_claims(), nonce check included. Held below 6 by in/constraints.in.
PIP_AUDIT_IGNORE += CVE-2026-115910
python-audit: ## Fail when a Python lockfile pins a release with a known vulnerability
	pip install --quiet "pip-audit==$(PIP_AUDIT_VERSION)"
	set -e; for lockfile in $(PIP_AUDIT_LOCKFILES); do \
		echo "pip-audit smarter/requirements/$$lockfile.txt"; \
		pip-audit --no-deps --disable-pip --progress-spinner off \
			$(foreach id,$(PIP_AUDIT_IGNORE),--ignore-vuln $(id)) \
			-r smarter/requirements/$$lockfile.txt; \
	done


# ---------------------------------------------------------
# Web console
# ---------------------------------------------------------
# The web console, smarter-sh/smarter-console: its release that smarter-console-version.txt pins, into
# smarter/smarter/static/react/, where collectstatic and the Docker build pick it up. See scripts/fetch_console.py.
console: ## Install the pinned release of the web console into the static folder
	python3 -I scripts/fetch_console.py

# A local build of the web console instead, to try a console change here before it is released:
# make build in a smarter-console checkout, then make console-local CONSOLE_DIST=../smarter-console/dist
console-local: ## Install a local smarter-console build: CONSOLE_DIST=../smarter-console/dist
	python3 -I scripts/fetch_console.py --from-dir $(or $(CONSOLE_DIST),../smarter-console/dist)

# Regenerate the Smarter Chat api contract's JSON Schema and examples from its Pydantic models
# (smarter.apps.prompt.contract.models), in the smarter-api container. Run it after changing the
# models, and commit the changes. smarter-console copies the schema into Smarter Chat, which generates
# its TypeScript types from it, with its make contracts.
CHAT_CONTRACT_SCHEMA := smarter/apps/prompt/contract/chat-contract.schema.json
CHAT_CONTRACT_EXAMPLE := smarter/apps/prompt/contract/chat-contract.example.json
chat-contract: ## Regenerate the Smarter Chat api contract schema and example
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_chat_contract_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(CHAT_CONTRACT_SCHEMA) smarter/$(CHAT_CONTRACT_SCHEMA)
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_chat_contract_example"
	docker cp smarter-api:/home/smarter_user/smarter/$(CHAT_CONTRACT_EXAMPLE) smarter/$(CHAT_CONTRACT_EXAMPLE)

# Regenerate the web console's message catalogs, smarter/smarter/locale/<language>/LC_MESSAGES/django.po
# (Django templates and Python) and djangojs.po (the web console's messages, from the pinned smarter-console
# release's messages.js, which make console installs in smarter/console/i18n/), for every language in
# settings.LANGUAGES, or only LANGUAGE=<code>, and compile them, in the smarter-api container. Translations
# already in the .po files are kept. Run make build first, so that the container has the current templates and code.
I18N_LOCALE_DIR := smarter/locale
CONSOLE_MESSAGES := smarter/console/i18n/messages.js
i18n-messages: ## Regenerate and compile the web console translations (.po), optionally LANGUAGE=<code>
	@test -f $(CONSOLE_MESSAGES) || { echo >&2 "$(CONSOLE_MESSAGES) is missing: run make console."; exit 1; }
	docker exec smarter-api mkdir -p /home/smarter_user/smarter/console/i18n
	docker cp $(CONSOLE_MESSAGES) smarter-api:/home/smarter_user/$(CONSOLE_MESSAGES)
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py update_console_messages $(if $(LANGUAGE),--language $(LANGUAGE),)"
	mkdir -p smarter/$(I18N_LOCALE_DIR)
	docker cp smarter-api:/home/smarter_user/smarter/$(I18N_LOCALE_DIR)/. smarter/$(I18N_LOCALE_DIR)/

# Regenerate the web console's Extensions api contract from its Pydantic models, in the smarter-api
# container. smarter-console copies it into @smarter/extension-console with its make contracts.
EXTENSION_CONTRACT_SCHEMA := smarter/apps/llmtool/extension/extension-console.schema.json
extension-contract: ## Regenerate the web console Extensions api contract schema
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_extension_console_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(EXTENSION_CONTRACT_SCHEMA) smarter/$(EXTENSION_CONTRACT_SCHEMA)

# Regenerate the LLMTool list's Extensions tab api contract from its Pydantic models, in the
# smarter-api container. smarter-console copies it into @smarter/llmtool-list with its make contracts.
LLMTOOL_LIST_CONTRACT_SCHEMA := smarter/apps/llmtool/views/listview/extension-list.schema.json
llmtool-list-contract: ## Regenerate the LLMTool list Extensions tab contract schema
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_extension_list_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(LLMTOOL_LIST_CONTRACT_SCHEMA) smarter/$(LLMTOOL_LIST_CONTRACT_SCHEMA)

# Regenerate the LLMClient deployment page's contract from its Pydantic models, in the smarter-api
# container. smarter-console copies it into @smarter/llmclient-deployment with its make contracts.
LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA := smarter/apps/llmclient/views/llmclient-deployment.schema.json
llmclient-deployment-contract: ## Regenerate the LLMClient deployment page contract schema
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_llmclient_deployment_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA) smarter/$(LLMCLIENT_DEPLOYMENT_CONTRACT_SCHEMA)

# Regenerate the contract of the workbench's Architecture tab, an LLMClient's tree of SAM resources, from its
# Pydantic models, in the smarter-api container. smarter-console copies it into @smarter/llmclient-architecture
# with its make contracts.
LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA := smarter/apps/prompt/views/detailviews/llmclient-architecture.schema.json
llmclient-architecture-contract: ## Regenerate the workbench Architecture tab contract schema
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_llmclient_architecture_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA) smarter/$(LLMCLIENT_ARCHITECTURE_CONTRACT_SCHEMA)

# Regenerate the web console session's contract, GET /api/web/session/, from its Pydantic models, in the
# smarter-api container. smarter-console copies it into @smarter/console with its make contracts.
CONSOLE_SESSION_CONTRACT_SCHEMA := smarter/apps/api/web/session/console-session.schema.json
console-session-contract: ## Regenerate the web console session contract schema
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_console_session_schema"
	docker cp smarter-api:/home/smarter_user/smarter/$(CONSOLE_SESSION_CONTRACT_SCHEMA) smarter/$(CONSOLE_SESSION_CONTRACT_SCHEMA)

# Regenerate the Smarter api contract from the platform's Pydantic models, in the smarter-api
# container: the SAM JSON Schemas and examples (one per kind) and the api's OpenAPI document, which the
# smarter cli and the SDKs generate their clients from. Run it after changing a SAM model, the
# journal contract or the cli api, and commit the files.
API_CONTRACT_DIR := smarter/apps/api/v1/contract
chart-credentials: ## Regenerate the map of each credential to the pods that hold it, and copy it into the Helm chart
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_chart_credentials"
	docker cp smarter-api:/home/smarter_user/smarter/smarter/common/conf/credentials.json smarter/smarter/common/conf/credentials.json
	mkdir -p helm/charts/smarter/files
	cp smarter/smarter/common/conf/credentials.json helm/charts/smarter/files/credentials.json

api-contract: ## Regenerate the SAM JSON Schemas and examples, and the api OpenAPI document
	docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py export_api_contract"
	docker cp smarter-api:/home/smarter_user/smarter/$(API_CONTRACT_DIR)/openapi.json smarter/$(API_CONTRACT_DIR)/openapi.json
	rm -f smarter/$(API_CONTRACT_DIR)/sam/*.schema.json
	docker cp smarter-api:/home/smarter_user/smarter/$(API_CONTRACT_DIR)/sam/. smarter/$(API_CONTRACT_DIR)/sam/

# -------------------------------------------------------------------------
# Sphinx Documentation
#
# automated ci-cid build target for Sphinx documentation
# python -m sphinx -T -b html -d _build/doctrees -D language=en . $READTHEDOCS_OUTPUT/html
#
# our local build target for Sphinx documentation is intended to try to match
# what ReadTheDocs does as closely as possible.
# -------------------------------------------------------------------------
sphinx-init: ## Initialize Sphinx documentation environment
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

sphinx-docs: ## Build Sphinx documentation
	@echo ""
	@echo "==============================================================================="
	@echo "Building Sphinx documentation using local Python environment."
	@echo "This may take a few minutes..."
	@echo "==============================================================================="
	cd docs && make SPHINXOPTS="-j auto -W -T -D language=en" html

sphinx-linkcheck: ## Check documentation links
	cd docs && make linkcheck

# the bucket and distribution come from the Terraform stack's outputs (make terraform-apply), as
# in smarter-python, smarter-types and cache-results. CloudFront reads the bucket through its OAC,
# so the objects need no public ACL. publish.yml runs the same two commands.
sphinx-publish: ## Publish documentation to AWS S3 and invalidate CloudFront cache
	BUCKET=$$($(TF) output -raw bucket_name) && \
	DISTRIBUTION=$$($(TF) output -raw distribution_id) && \
	aws s3 sync docs/build/html "s3://$$BUCKET/" --delete --exclude ".doctrees/*" --exclude ".buildinfo" --exclude ".buildinfo.bak" && \
	aws cloudfront create-invalidation --distribution-id "$$DISTRIBUTION" --paths "/*" --query Invalidation.Id --output text

# docs.smarter.sh's AWS resources (terraform/docs). Terraform runs as the caller's AWS
# profile; the account id is only needed for the state bucket's name, never written here.
TF := terraform -chdir=terraform/docs

terraform-init: ## Initialize the docs.smarter.sh stack (terraform/docs) and its state
	$(TF) init -backend-config="bucket=$$(aws sts get-caller-identity --query Account --output text)-terraform-tfstate-smarter"

terraform-plan: ## Plan changes to docs.smarter.sh AWS resources, into terraform/docs/tfplan
	$(TF) plan -out=tfplan

terraform-apply: ## Apply terraform/docs/tfplan
	$(TF) apply tfplan
	rm -f terraform/docs/tfplan

help: ## Show this menu of commands
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}'
