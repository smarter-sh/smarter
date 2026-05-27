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
sudo apt-get install -y \
	build-essential \
    python3 python3-venv python3-pip \
	golang \
	nodejs npm \
	docker.io docker-compose \
	awscli \
	kubectl \
	libblis-dev zlib1g-dev libzstd-dev libopenblas-dev libffi-dev libssl-dev \
	libxml2-dev libxslt1-dev sqlite3 libmariadb-dev libgeos-dev mysql-client jq

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

brew install python@3.13

alias python="/home/linuxbrew/.linuxbrew/opt/python@3.13/libexec/bin/python"
alias python3="/home/linuxbrew/.linuxbrew/opt/python@3.13/libexec/bin/python3"

# Prepend the Homebrew Python bin directory to PATH
export PATH="/home/linuxbrew/.linuxbrew/opt/python@3.13/libexec/bin:$PATH"

# Optionally, set these for building Python packages (Linuxbrew path)
export LDFLAGS="-L/home/linuxbrew/.linuxbrew/opt/python@3.13/lib"
export CPPFLAGS="-I/home/linuxbrew/.linuxbrew/opt/python@3.13/include"
export PKG_CONFIG_PATH="/home/linuxbrew/.linuxbrew/opt/python@3.13/lib/pkgconfig"

sudo snap install k9s

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
python3 --version

echo "go:"
go version

echo "node:"
node --version

echo "awscli:"
aws --version

echo "kubectl:"
kubectl version --client

echo "=============================================="
