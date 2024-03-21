SHELL := /bin/bash
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

.PHONY: analyze pre-commit python-init python-activate python-lint python-clean python-test react-init react-lint react-update react-run react-build react-release

# Default target executed when no arguments are given to make.
all: help

clean:
	make python-clean
	make react-clean

lint:
	make python-lint
	make react-lint

init:
	make python-init
	make react-init

build:
	make aws-build
	make react-build

run:
	make react-run

analyze:
	cloc . --exclude-ext=svg,json,zip --fullpath --not-match-d=smarter/smarter/static/assets/ --vcs=git

coverage:
	docker exec -it smarter-app-1 bash -c "coverage run manage.py test && coverage report -m && coverage html"

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
docker-init:
	docker exec -it smarter-mysql-1 mysql -u smarter -psmarter -e 'DROP DATABASE IF EXISTS smarter; CREATE DATABASE smarter;' && \
	docker exec -it smarter-app-1 bash -c "python manage.py makemigrations && python manage.py migrate && python manage.py create_user --username admin --email admin@smarter.sh --password smarter --admin && python manage.py add_plugin_examples admin && python manage.py seed_chat_history"

docker-build:
	docker-compose up --build

docker-run:
	make docker-collectstatic
	docker-compose up

docker-collectstatic:
	(cd smarter/smarter/apps/chatapp/reactapp/ && npm run build)
	(cd smarter && python manage.py collectstatic --noinput)

docker-test:
	docker exec -it smarter-app-1 bash -c "python manage.py test"

docker-test-ubuntu:
	docker exec app bash -c "python manage.py test"


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
	@echo 'clean              - remove all build, test, coverage and Python artifacts'
	@echo 'lint               - run all code linters and formatters'
	@echo 'init               - create environments for Python, NPM and pre-commit and install dependencies'
	@echo 'build              - create and configure AWS infrastructure resources and build the React app'
	@echo 'run                - run the web app in development mode'
	@echo 'analyze            - generate code analysis report'
	@echo 'coverage           - generate code coverage analysis report'
	@echo 'release            - force a new release'
	@echo '-- AWS --'
	@echo 'aws-build          - run Terraform to create AWS infrastructure'
	@echo '-- Python-Django API --'
	@echo 'python-init        - create a Python virtual environment and install dependencies'
	@echo 'python-test        - run Python unit tests'
	@echo 'python-lint        - run Python linting'
	@echo 'python-clean       - destroy the Python virtual environment'
	@echo '-- Keen --'
	@echo 'keen-init          - install gulp, yarn and dependencies'
	@echo 'keen-build         - build Keen app'
	@echo 'keen-server        - start local Keen web server'
	@echo '-- React App --'
	@echo 'react-clean        - destroy npm environment'
	@echo 'react-init         - run npm install'
	@echo 'react-lint         - run npm lint'
	@echo 'react-update       - update npm packages'
	@echo 'react-run          - run the React app in development mode'
	@echo 'react-build        - build the React app for production'
	@echo 'react-release      - deploy the React app to AWS S3 and invalidate the Cloudfront CDN'
