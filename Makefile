SHELL := /bin/bash
include .env
export

ifeq ($(OS),Windows_NT)
    PYTHON := python.exe
    ACTIVATE_VENV := venv\Scripts\activate
else
    PYTHON := python3.11
    ACTIVATE_VENV := source venv/bin/activate
endif
PIP := $(PYTHON) -m pip

ifneq ("$(wildcard .env)","")
else
    $(shell cp ./doc/example-dot-env .env)
endif

.PHONY: init activate build run clean tear-down lint analyze coverage release pre-commit-init pre-commit-run python-init python-activate python-lint python-clean python-test react-init react-lint react-update react-run react-build terraform-build terraform-clean docker-init docker-build docker-run docker-collectstatic docker-test python-init python-lint python-clean keen-init keen-build keen-server react-clean react-init react-lint react-update react-run react-build help

# Default target executed when no arguments are given to make.
all: help

# initialize local development environment.
# takes around 5 minutes to complete
init:
	make check-python		# verify Python 3.11 is installed
	make check-docker		# verify Docker is installed and running
	make tear-down			# start w a clean environment
	make python-init		# create/replace Python virtual environment and install dependencies
	make docker-build		# build Docker containers
	make docker-run			# start all Docker containers
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

clean:
	make python-clean
	make react-clean
	make terraform-clean
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
	make react-lint

analyze:
	cloc . --exclude-ext=svg,json,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

coverage:
	docker exec smarter-app bash -c "coverage run manage.py test && coverage report -m && coverage html"

pre-commit-init:
	pre-commit install
	pre-commit autoupdate
	pre-commit run --all-files

pre-commit-run:
	pre-commit run --all-files

release:
	git commit -m "fix: force a new release" --allow-empty && git push


# ---------------------------------------------------------
# Docker
# ---------------------------------------------------------
check-docker:
	@docker ps >/dev/null 2>&1 || { echo >&2 "This project requires Docker but it's not running.  Aborting."; exit 1; }

docker-shell:
	make check-docker
	docker exec -it smarter-app /bin/bash

docker-init:
	make check-docker
	docker-compose up -d
	@echo "Initializing Docker..." && \
	docker exec smarter-mysql bash -c "sleep 20; until echo '\q' | mysql -u smarter -psmarter; do sleep 10; done" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter;' && \
	docker exec smarter-app bash -c "python manage.py makemigrations && python manage.py migrate && python manage.py create_user --username admin --email admin@smarter.sh --password smarter --admin && python manage.py add_plugin_examples admin && python manage.py seed_chat_history"
	docker ps

docker-build:
	make check-docker
	docker-compose build

docker-run:
	make check-docker
	docker-compose up

docker-collectstatic:
	make check-docker
	docker-compose up -d
	(cd smarter/smarter/apps/chatapp/reactapp/ && npm run build)
	(docker exec smarter-app bash -c "python manage.py  collectstatic --noinput")
	docker-compose down

docker-test:
	make check-docker
	make docker-init
	docker-compose up -d
	docker exec smarter-app bash -c "python manage.py test"
	docker-compose down

docker-prune:
	make check-docker
	find ./ -name celerybeat-schedule -type f -exec rm -f {} +
	docker system prune -a
	docker volume prune -f
	docker builder prune -a -f

# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
check-python:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo >&2 "This project requires $(PYTHON) but it's not installed.  Aborting."; exit 1; }

python-init:
	make check-python
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install -r smarter/requirements/local.txt

python-lint:
	make check-python
	make pre-commit-run

python-clean:
	rm -rf venv
	find ./ -name __pycache__ -type d -exec rm -rf {} +

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
# React app
# ---------------------------------------------------------
react-clean:
	rm -rf node_modules
	rm -rf react/node_modules
	rm -rf react/dist

react-init:
	make react-clean
	npm install
	cd ./smarter/smarter/apps/chatapp/reactapp/ && npm install && npm init @eslint/config

react-lint:
	cd ./react && npm run lint
	# npx prettier --write "./smarter/smarter/apps/chatapp/reactapp/src/**/*.{js,cjs,jsx,ts,tsx,json,css,scss,md}"

react-update:
	npm install -g npm
	npm install -g npm-check-updates
	ncu --upgrade --packageFile ./smarter/smarter/apps/chatapp/reactapp/package.json
	npm update -g
	npm install ./smarter/smarter/apps/chatapp/reactapp/

react-run:
	cd ./smarter/smarter/apps/chatapp/reactapp/ && npm run dev

react-build:
	cd ./smarter/smarter/apps/chatapp/reactapp/ && npm run build


# -------------------------------------------------------------------------
# AWS and deployment
# -------------------------------------------------------------------------
terraform-build:
	cd aws
	terraform init
	terraform apply

terraform-clean:
	find ./ -name .terragrunt-cache -type d -exec rm -rf {} +
	find ./ -name .terraform.lock.hcl -type f -exec rm {} +

helm-update:
	cd helm/charts/smarter && \
	helm dependency update


######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'init                   - Initialize local and Docker environments'
	@echo 'activate               - activates Python virtual environment'
	@echo 'build                  - Build Docker containers'
	@echo 'run                    - run web application from Docker'
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
	@echo 'terraform-build        - Run Terraform to create AWS infrastructure'
	@echo 'terraform-clean        - Prune Terraform cache and lock files'
	@echo 'helm-update            - Update Helm chart dependencies'
	@echo '<************************** Python **************************>'
	@echo 'python-init            - Create a Python virtual environment and install dependencies'
	@echo 'python-lint            - Run Python linting using pre-commit'
	@echo 'python-clean           - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo '<************************** Docker **************************>'
	@echo 'docker-init            - Initialize MySQL and create the smarter database'
	@echo 'docker-build           - Build all Docker containers using docker-compose'
	@echo 'docker-run             - Start all Docker containers using docker-compose'
	@echo 'docker-collectstatic   - Run Django collectstatic in Docker'
	@echo 'docker-test            - Run Python-Django unit tests in Docker'
	@echo '<************************** Keen **************************>'
	@echo 'keen-init              - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build             - Build Keen app using gulp'
	@echo 'keen-server            - Start local Keen web server using gulp'
	@echo '<************************** React **************************>'
	@echo 'react-clean            - Remove node_modules directories for React app'
	@echo 'react-init             - Run npm install for React app'
	@echo 'react-lint             - Run npm lint for React app'
	@echo 'react-update           - Update npm packages for React app'
	@echo 'react-run              - Run the React app in development mode'
	@echo 'react-build            - Build the React app for production'
	@echo '===================================================================='
