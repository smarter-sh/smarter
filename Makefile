SHELL := /bin/bash
S3_BUCKET := smarter.sh
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
	cloc . --exclude-ext=svg,json,zip --vcs=git

coverage:
	coverage run --source=python/smarter \
				 -m unittest discover -s python/smarter/
	coverage report -m
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
# Python Djanog API
# ---------------------------------------------------------
python-init:
	make python-clean
	npm install && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install -r requirements/local.txt && \
	pre-commit install

python-test:
	cd python/smarter && python manage.py test

python-lint:
	terraform fmt -recursive
	pre-commit run --all-files
	black ./python/
	flake8 api/terraform/python/
	pylint python/smarter/**/*.py

python-clean:
	rm -rf venv
	find python/ -name __pycache__ -type d -exec rm -rf {} +

python-run:
	cd python/smarter && python manage.py runserver

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
	@echo 'clean               - remove all build, test, coverage and Python artifacts'
	@echo 'lint                - run all code linters and formatters'
	@echo 'init                - create environments for Python, NPM and pre-commit and install dependencies'
	@echo 'build               - create and configure AWS infrastructure resources and build the React app'
	@echo 'run                 - run the web app in development mode'
	@echo 'analyze             - generate code analysis report'
	@echo 'coverage            - generate code coverage analysis report'
	@echo 'release             - force a new release'
	@echo '-- AWS API Gateway + Lambda --'
	@echo 'python-init            - create a Python virtual environment and install dependencies'
	@echo 'python-test            - run Python unit tests'
	@echo 'python-lint            - run Python linting'
	@echo 'python-clean           - destroy the Python virtual environment'
	@echo '-- React App --'
	@echo 'react-clean        - destroy npm environment'
	@echo 'react-init         - run npm install'
	@echo 'react-lint         - run npm lint'
	@echo 'react-update       - update npm packages'
	@echo 'react-run          - run the React app in development mode'
	@echo 'react-build        - build the React app for production'
	@echo 'react-release      - deploy the React app to AWS S3 and invalidate the Cloudfront CDN'
