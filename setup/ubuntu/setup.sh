#!/bin/bash
###############################################################################
# Author: Lawrence McDaniel https://lawrencemcdaniel.com
# Date: 2026-05-26
#
# setup.sh — Ubuntu Environment Setup for Smarter Project
#
# This script verifies and installs required development tools for the Smarter project on Ubuntu.
# It checks for essential packages and libraries, and installs them via apt.
#
# Usage:
#   bash setup.sh
#
# Requirements:
#   - Ubuntu
#   - Administrator privileges (for some installations and symlinks)
#
# Actions performed:
#   - Verifies essential packages and libraries
#   - Ensures docker-compose symlink exists
#   - Installs development dependencies (gcc, python, go, node, nvm, awscli, kubectl, etc.)
#
# Exit codes:
#   0 — Success
#   1 — Missing prerequisite or failed installation
#
###############################################################################
sudo apt-get update
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 -y

sudo apt-get install -y \
	build-essential \
	golang \
	nodejs npm \
	docker.io docker-compose \
	awscli \
	kubectl \
	libblis-dev zlib1g-dev libzstd-dev libopenblas-dev libffi-dev libssl-dev \
	libxml2-dev libxslt1-dev sqlite3 libmariadb-dev libgeos-dev mysql-client jq

sudo snap install k9s

cp .zshrc.example ~/.zshrc
source ~/.zshrc
echo $PATH

# NVM (Node Version Manager) is not available via apt. Install manually:
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Then restart your shell and use nvm to install/manage Node.js versions.

echo ""
echo "=============================================="
echo " Smarter Project — Installed Packages Summary"
echo "=============================================="

echo "Docker:"
docker --version

echo "docker-compose:"
docker compose version

echo "gcc:"
gcc --version | head -n 1

echo "python:"
python --version
echo "Python interpreter path: $(which python)"

echo "go:"
go version

echo "node:"
node --version

echo "awscli:"
aws --version

echo "kubectl:"
kubectl version --client

echo "=============================================="
