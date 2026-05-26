#!/bin/bash
###############################################################################
# Author: Lawrence McDaniel https://lawrencemcdaniel.com
# Date: 2026-05-26
#
# setup.sh — macOS Environment Setup for Smarter Project
#
# This script verifies and installs required development tools for the Smarter project on macOS.
# It checks for Xcode Command Line Tools, Homebrew, and Docker Desktop, and installs essential
# packages and libraries via Homebrew.
#
# Usage:
#   bash setup.sh
#
# Requirements:
#   - macOS
#   - Administrator privileges (for some installations and symlinks)
#
# Actions performed:
#   - Verifies Xcode Command Line Tools, Homebrew, Docker Desktop
#   - Ensures docker-compose symlink exists
#   - Installs development dependencies (gcc, python, go, node, nvm, awscli, kubectl, etc.)
#
# Exit codes:
#   0 — Success
#   1 — Missing prerequisite or failed installation
#
###############################################################################

# open "macappstore://itunes.apple.com/app/id497799835"
xcode-select --install


# Verify prerequisites: Xcode, Homebrew, Docker Desktop
echo "[INFO] Verifying required tools..."

# Check for Xcode Command Line Tools
if ! xcode-select -p &>/dev/null; then
	echo -e "\033[0;31m[ERROR]\033[0m Xcode Command Line Tools are not installed."
	echo "Please install them by running: xcode-select --install"
	exit 1
else
	echo -e "\033[0;32m[OK]\033[0m Xcode Command Line Tools are installed."
fi

# Check for Homebrew
if ! command -v brew &>/dev/null; then
	echo -e "\033[0;31m[ERROR]\033[0m Homebrew is not installed."
	echo "Please install Homebrew from https://brew.sh/"
	exit 1
else
	echo -e "\033[0;32m[OK]\033[0m Homebrew is installed."
fi

# Check for Docker Desktop
if ! command -v docker &>/dev/null; then
	echo -e "\033[0;31m[ERROR]\033[0m Docker is not installed."
	echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/"
	exit 1
else
	echo -e "\033[0;32m[OK]\033[0m Docker Desktop is installed."
fi


# Ensure /usr/local/bin/docker-compose symlink exists
if [ ! -L "/usr/local/bin/docker-compose" ]; then
	echo -e "\033[0;34m[INFO]\033[0m Creating symlink for docker-compose in /usr/local/bin..."
	sudo ln -sf "/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose" "/usr/local/bin/docker-compose"
	if [ $? -eq 0 ]; then
		echo -e "\033[0;32m[OK]\033[0m Symlink created: /usr/local/bin/docker-compose -> /Applications/Docker.app/Contents/Resources/bin/docker-compose"
	else
		echo -e "\033[0;31m[ERROR]\033[0m Failed to create symlink for docker-compose."
		exit 1
	fi
else
	echo -e "\033[0;32m[OK]\033[0m Symlink for docker-compose exists."
fi

brew install gcc python@3.13 go node nvm
brew install awscli kubectl
brew install blis zlib zstd openblas libffi openssl libxml2 libxslt sqlite mariadb-connector-c geos mysql-client jq k9s

echo ""
echo "=============================================="
echo " Smarter Project — Installed Packages Summary"
echo "=============================================="

echo "Xcode Command Line Tools:"
xcode-select -v

echo "Homebrew:"
brew --version | head -n 1

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

echo "Other Homebrew packages:"
brew list --versions blis zlib zstd openblas libffi openssl libxml2 libxslt sqlite mariadb-connector-c geos mysql-client jq k9s

echo "=============================================="
