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
#   - Installs Python 3.14, Docker with Compose v2, and the native build libraries via apt
#   - Ensures docker-compose symlink exists
#   - Installs awscli, kubectl, helm, go and k9s via snap, and Node.js 24 via nvm
#
# Exit codes:
#   0 — Success
#   1 — Missing prerequisite or failed installation
#
###############################################################################
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo apt-get update
sudo apt-get install -y software-properties-common curl

# Python 3.14, from the deadsnakes PPA
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.14-venv python3.14-dev

# Docker, with the Compose v2 plugin. The Makefile calls both "docker compose" and
# "docker-compose", so link the plugin to the second name too.
sudo apt-get install -y docker.io docker-compose-v2
if [ ! -e /usr/local/bin/docker-compose ]; then
	sudo ln -sf /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
fi

# Native libraries that the local Python virtual environment builds against
sudo apt-get install -y \
	build-essential \
	libblis-dev zlib1g-dev libzstd-dev libopenblas-dev libffi-dev libssl-dev \
	libxml2-dev libxslt1-dev sqlite3 libmariadb-dev libmariadb-dev-compat libgeos-dev mysql-client jq

# Tools that Ubuntu's archive doesn't carry, or carries in versions too old for Smarter
sudo snap install aws-cli --classic
sudo snap install kubectl --classic
sudo snap install helm --classic
sudo snap install go --classic
sudo snap install k9s

# Node.js 24 or later, through nvm (the archive's nodejs is older)
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
. "$NVM_DIR/nvm.sh"
nvm install 24
nvm alias default 24

echo ""
echo "[INFO] Merge the settings you need from $SCRIPT_DIR/.zshrc.example into your ~/.zshrc,"
echo "       then open a new shell. It is a template, not a replacement for your own ~/.zshrc."

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
python3.14 --version
echo "Python interpreter path: $(which python3.14)"

echo "go:"
go version

echo "node:"
node --version

echo "awscli:"
aws --version

echo "kubectl:"
kubectl version --client

echo "helm:"
helm version --short

echo "=============================================="
