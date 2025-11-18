# !/bin/bash
# Script to verify the Helm chart signature for Artifact Hub using Cosign
# Usage: ./artifacthub-cosign-verify.sh <version>

if [ -z "$1" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

VERSION="$1"

cosign verify --key ../sigstore/artifacthub-cosign.pub ghcr.io/smarter-sh/charts/smarter:"$VERSION"
