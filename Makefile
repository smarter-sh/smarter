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
	cloc . --exclude-ext=svg,json,zip --fullpath --not-match-d=smarter/smarter/static --vcs=git

coverage:
	cd smarter && \
	coverage run manage.py test && \
	coverage report -m && \
	coverage html

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
django-init:
	if [ -f smarter/smarter/db.sqlite3 ]; then rm smarter/smarter/db.sqlite3; fi && \
	cd smarter && python manage.py makemigrations && \
	python manage.py migrate && \
	python manage.py create_admin_user --username admin --email admin@smarter.sh --password smarter && \
	python manage.py add_plugin_examples admin && \
	python manage.py seed_chat_history

django-run:
	cd smarter && python manage.py runserver

django-collectstatic:
	(cd smarter/smarter/apps/chatapp/reactapp/ && npm run build)
	(cd smarter && python manage.py collectstatic --noinput)

django-test:
	cd smarter && python manage.py test


# ---------------------------------------------------------
# Python
# ---------------------------------------------------------
python-init:
	make python-clean
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install -r smarter/requirements/local.txt && \
	pre-commit install && \
	make django-init

python-lint:
	terraform fmt -recursive
	pre-commit run --all-files
	black ./smarter/
	flake8 api/terraform/python/
	pylint smarter/**/*.py

python-clean:
	rm -rf venv
	find python/ -name __pycache__ -type d -exec rm -rf {} +

# ---------------------------------------------------------
# Keen
# ---------------------------------------------------------
keen-init:
	cd keen_v3.0.6/tools && npm install --globar yarn && \
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
	cd ./react && npm install && npm init @eslint/config

react-lint:
	cd ./react && npm run lint
	# npx prettier --write "src/**/*.{js,cjs,jsx,ts,tsx,json,css,scss,md}"

react-update:
	npm install -g npm
	npm install -g npm-check-updates
	ncu --upgrade --packageFile ./package.json
	ncu --upgrade --packageFile ./react/package.json
	npm update -g
	npm install ./react/

react-run:
	cd ./react && npm run dev

react-build:
	cd ./react && npm run build

react-release:
	#---------------------------------------------------------
	# usage:      deploy prouduction build of the React
	#             app to AWS S3 bucket.
	#
	#             1. Build the React application
	#             2. Upload to AWS S3
	#             3. Invalidate all items in the AWS Cloudfront CDN.
	#---------------------------------------------------------
	npm run build --prefix ./react/

	# ------------------------
	# add all built files to the S3 bucket.
	# ------------------------
	aws s3 sync ./react/dist/ s3://$(S3_BUCKET) \
				--acl public-read \
				--delete --cache-control max-age=31536000,public \
				--expires '31 Dec 2050 00:00:01 GMT'

	# ------------------------
	# remove the cache-control header created above with a "no-cache" header so that browsers never cache this page
	# ------------------------
	aws s3 cp s3://$(S3_BUCKET)/index.html s3://$(S3_BUCKET)/index.html --metadata-directive REPLACE --cache-control max-age=0,no-cache,no-store,must-revalidate --content-type text/html --acl public-read

	# invalidate the Cloudfront cache
	aws cloudfront create-invalidation --distribution-id $(CLOUDFRONT_DISTRIBUTION_ID) --paths "/*" "/index.html"

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
