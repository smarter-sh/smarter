#!/bin/bash
# Script to generate the Cosign public key fingerprint for Artifact Hub
# Usage: ./artifacthub-cosign-fingerprint.sh
#
# This script computes the SHA-256 fingerprint of the Cosign public key
# this belongs in the Helm chart's Chart.yaml under artifacthub.io/signKey.fingerprint
shasum -a 256 ../sigstore/artifacthub-cosign.pub | awk '{print toupper($1)}'
