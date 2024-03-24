SHELL := /bin/bash
include .env
export
S3_BUCKET := dev.platform.smarter.sh
CLOUDFRONT_DISTRIBUTION_ID := E3AIBM1KMSJOP1

ifeq ($(OS),Windows_NT)
    PYTHON := python.exe
    ACTIVATE_VENV := venv\Scripts\activate
else
    PYTHON := python3.11
    ACTIVATE_VENV := source venv/bin/activate
endif
PIP := $(PYTHON) -m pip

ifneq ("$(wildcard .env)","")
    include .env
else
    $(shell cp ./doc/example-dot-env .env)
endif

.PHONY: analyze pre-commit python-init python-activate python-lint python-clean python-test react-init react-lint react-update react-run react-build aws-build docker-init docker-build docker-run docker-collectstatic docker-test python-init python-lint python-clean keen-init keen-build keen-server react-clean react-init react-lint react-update react-run react-build help

# Default target executed when no arguments are given to make.
all: help

clean:
	make python-clean
	make react-clean

lint:
	make python-lint
	make react-lint

init:
	make docker-init

build:
	make docker-build

analyze:
	cloc . --exclude-ext=svg,json,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

coverage:
	docker exec smarter-app bash -c "coverage run manage.py test && coverage report -m && coverage html"

release:
	git commit -m "fix: force a new release" --allow-empty && git push

pre-commit:
	pre-commit install
	pre-commit autoupdate
	pre-commit run --all-files

# -------------------------------------------------------------------------
# AWS
# -------------------------------------------------------------------------
aws-build:
	cd aws
	terraform init
	terraform apply

# ---------------------------------------------------------
# Django Back End
# ---------------------------------------------------------
helm-update:
	cd helm/charts/smarter && \
	helm dependency update

docker-init:
	@echo "Initializing Docker..." && \
	docker exec smarter-mysql bash -c "until echo '\q' | mysql -u smarter -psmarter; do sleep 1; done" && \
	docker exec smarter-mysql mysql -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter;' && \
	docker exec smarter-app bash -c "python manage.py makemigrations && python manage.py migrate && python manage.py create_user --username admin --email admin@smarter.sh --password smarter --admin && python manage.py add_plugin_examples admin && python manage.py seed_chat_history"

docker-build:
	docker-compose up --build

docker-run:
	make docker-collectstatic
	docker-compose up

docker-collectstatic:
	(cd smarter/smarter/apps/chatapp/reactapp/ && npm run build)
	(docker exec smarter-app bash -c "python manage.py  collectstatic --noinput")

docker-test:
	docker exec smarter-app bash -c "python manage.py test"


# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
python-init:
	make python-clean && \
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install -r smarter/requirements/local.txt && \
	pre-commit install

python-lint:
	make pre-commit

python-clean:
	rm -rf smarter/venv
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

######################
# React app
######################
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


######################
# HELP
######################

help:
	@echo '===================================================================='
	@echo 'clean              - Remove all build, test, coverage and Python artifacts'
	@echo 'lint               - Run all code linters and formatters'
	@echo 'init               - Initialize Docker MySQL database and Django migrations'
	@echo 'build              - Build Docker containers'
	@echo 'analyze            - Generate code analysis report using cloc'
	@echo 'coverage           - Generate Docker-based code coverage analysis report'
	@echo 'release            - Force a new Github release'
	@echo '-- AWS --'
	@echo 'aws-build          - Run Terraform to create AWS infrastructure'
	@echo '-- Python-Django Dashboard application --'
	@echo 'python-init        - Create a Python virtual environment and install dependencies'
	@echo 'python-lint        - Run Python linting using pre-commit'
	@echo 'python-clean       - Destroy the Python virtual environment and remove __pycache__ directories'
	@echo '-- Docker --'
	@echo 'docker-init        - Initialize MySQL and create the smarter database'
	@echo 'docker-build       - Build all Docker containers using docker-compose'
	@echo 'docker-run         - Start all Docker containers using docker-compose'
	@echo 'docker-collectstatic - Run Django collectstatic in Docker'
	@echo 'docker-test        - Run Python-Django unit tests in Docker'
	@echo '-- Keen --'
	@echo 'keen-init          - Install gulp, yarn and dependencies for Keen'
	@echo 'keen-build         - Build Keen app using gulp'
	@echo 'keen-server        - Start local Keen web server using gulp'
	@echo '-- React App --'
	@echo 'react-clean        - Remove node_modules directories for React app'
	@echo 'react-init         - Run npm install for React app'
	@echo 'react-lint         - Run npm lint for React app'
	@echo 'react-update       - Update npm packages for React app'
	@echo 'react-run          - Run the React app in development mode'
	@echo 'react-build        - Build the React app for production'
	@echo '===================================================================='
