#!/bin/bash
# Artifact Hub verification push script


source ../.env
echo $PAT | oras login ghcr.io -u mcdaniel0073 --password-stdin

cd ../helm/charts/smarter
oras push \
  ghcr.io/smarter-sh/charts/smarter:artifacthub.io \
  --config /dev/null:application/vnd.cncf.artifacthub.config.v1+yaml \
  artifacthub-repo.yml:application/vnd.cncf.artifacthub.repository-metadata.layer.v1.yaml

cd ../../../scripts
