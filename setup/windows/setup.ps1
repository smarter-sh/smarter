###############################################################################
# Author: Lawrence McDaniel https://lawrencemcdaniel.com
# Date: 2026-05-26
#
# setup.ps1 — Windows Environment Setup for Smarter Project
#
# This script verifies and installs required development tools for the Smarter project on Windows.
# It checks for essential packages and libraries, and installs them via winget.
#
# Usage:
#   powershell -File setup.ps1
#
# Requirements:
#   - Windows
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


# This script installs core dependencies using winget and pip where possible.
# Some scientific libraries may require manual installation or pre-built binaries.

# Ensure script runs as Administrator
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "You do not have Administrator rights to run this script! Please re-run as Administrator."
    break
}

# Update winget
winget upgrade --all --accept-source-agreements --accept-package-agreements

# Install core tools
winget install -e --id Python.Python.3
winget install -e --id GoLang.Go
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id AWS.AWSCLI
winget install -e --id Kubernetes.kubectl
winget install -e --id derailed.k9s

# Install Docker Desktop (includes Docker Compose)
winget install -e --id Docker.DockerDesktop

# Install Visual Studio Community (includes C++ build tools)
winget install -e --id Microsoft.VisualStudio.2022.Community

# Install nvm-windows (Node Version Manager for Windows)
winget install -e --id CoreyButler.NVMforWindows

# Install jq
winget install -e --id stedolan.jq

# Install MySQL client
winget install -e --id Oracle.MySQL

# Install MariaDB Connector/C
winget install -e --id MariaDB.Client

# Install SQLite
winget install -e --id SQLite.sqlite

# Note: For BLIS/OpenBLAS, zlib, zstd, libffi, OpenSSL, libxml2, libxslt, geos, you may need to use pre-built binaries or install via conda/other package managers if needed for Python/scientific stack.

# Upgrade pip and install Python packages if needed
python -m pip install --upgrade pip

# Example: Install scientific Python stack (optional, if needed)
# python -m pip install numpy scipy pandas matplotlib

Write-Host "\nSmarter development environment setup complete!\n"

Write-Host "`n=============================================="
Write-Host " Smarter Project — Installed Packages Summary"
Write-Host "=============================================="

Write-Host "Python:"
python --version

Write-Host "Go:"
go version

Write-Host "Node:"
node --version

Write-Host "nvm-windows:"
nvm version

Write-Host "AWS CLI:"
aws --version

Write-Host "kubectl:"
kubectl version --client --output=yaml

Write-Host "Docker:"
docker --version

Write-Host "Docker Compose:"
docker compose version

Write-Host "Visual Studio (C++ Build Tools):"
& "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.exe" /?

Write-Host "jq:"
jq --version

Write-Host "MySQL client:"
mysql --version

Write-Host "MariaDB Connector/C:"
# No direct CLI, but you can check if the DLL exists:
if (Test-Path "C:\Program Files\MariaDB\MariaDB Connector C 64-bit\bin\libmariadb.dll") {
    Write-Host "MariaDB Connector/C installed"
} else {
    Write-Host "MariaDB Connector/C not found"
}

Write-Host "SQLite:"
sqlite3 --version

Write-Host "=============================================="
