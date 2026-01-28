"""
Script to update the semantic version in pyproject.toml and Dockerfile.
Called automatically from semantic-release hooks.
see: release.config.js in the root directory.

Usage:
    python scripts/bump_version.py <new_version>

Updates:
- smarter/smarter/__version__.py
- pyproject.toml
- Dockerfile
- helm/charts/smarter/Chart.yaml
- helm/charts/smarter/values.yaml
- .github/actions/deploy/action.yml
"""

import re
import sys
from pathlib import Path


def update_version_in_file(filepath, pattern, replacement):
    path = Path(filepath)
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    path.write_text(new_text, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py <new_version>")
        sys.exit(1)
    new_version = sys.argv[1]

    # Validate semantic version: ##.##.##
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print("Error: Version must be in format ##.##.## (e.g., 0.1.20)")
        sys.exit(1)

    # Update __version__.py
    update_version_in_file(
        "smarter/smarter/__version__.py", r'__version__\s*=\s*["\'].*?["\']', f'__version__ = "{new_version}"'
    )
    print(f"Updated __version__.py to {new_version}")

    # Update pyproject.toml
    update_version_in_file("pyproject.toml", r'version\s*=\s*["\'].*?["\']', f'version = "{new_version}"')
    print(f"Updated pyproject.toml to {new_version}")

    # LABEL maintainer="Lawrence McDaniel <lpm0073@gmail.com>" \
    #   description="Docker image for the Smarter Api" \
    #   license="GNU AGPL v3" \
    #   vcs-url="https://github.com/smarter-sh/smarter" \
    #   org.opencontainers.image.title="Smarter API" \
    #   org.opencontainers.image.version="x.x.x" \
    #   org.opencontainers.image.authors="Lawrence McDaniel <lpm0073@gmail.com>" \
    #   org.opencontainers.image.url="https://smarter-sh.github.io/smarter/" \
    #   org.opencontainers.image.source="https://github.com/smarter-sh/smarter" \
    #   org.opencontainers.image.documentation="https://docs.smarter.sh/"
    update_version_in_file(
        "Dockerfile",
        r'org\.opencontainers\.image\.version="[^"]+"',
        f'org.opencontainers.image.version="{new_version}"',
    )
    print(f"Updated Dockerfile to {new_version}")

    # - name: Set Docker image
    #   id: set-docker-image
    #   shell: bash
    #   run: |-
    #     echo "SMARTER_DOCKER_IMAGE=mcdaniel0073/smarter:vx.x.x" >> $GITHUB_ENV
    #   env:
    #     AWS_ECR_REPO: ${{ env.NAMESPACE }}
    update_version_in_file(
        ".github/actions/deploy/action.yml",
        r'^(\s*echo\s+"SMARTER_DOCKER_IMAGE=mcdaniel0073/smarter:)(v\d+\.\d+\.\d+)(".*)$',
        f"\\g<1>v{new_version}\\g<3>",
    )
    print(f"Updated .github/actions/deploy/action.yml to {new_version}")

    # Update helm/charts/smarter/values.yaml
    # global:
    #   image:
    #     pullPolicy: IfNotPresent
    #     repository: lpm0073/smarter
    #     tag: vx.x.x
    update_version_in_file(
        "helm/charts/smarter/values.yaml",
        r"(tag:\s*)v\d+\.\d+\.\d+",
        f"\\g<1>v{new_version}",
    )
    print(f"Updated helm/charts/smarter/values.yaml to {new_version}")

    # -------------------------------------------------------------------------
    # Update helm/charts/smarter/Chart.yaml
    # -------------------------------------------------------------------------

    # Update appVersion in Chart.yaml
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r"(appVersion:\s*)[\d\.]+",
        f"\\g<1>{new_version}",
    )
    # Update version in Chart.yaml (top-level only)
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r"^version:\s*\d+\.\d+\.\d+$",
        f"version: {new_version}",
    )
    # Update image version in artifacthub.io/images in Chart.yaml
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r"(image:\s*mcdaniel0073/smarter:)(v?\d+\.\d+\.\d+)",
        f"\\g<1>v{new_version}",
    )
    # Update version in artifacthub.io/changes description in Chart.yaml
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r"(description: bump to app version )\d+\.\d+\.\d+",
        f"\\g<1>{new_version}",
    )
    # Update version in helm.sh/chart Chart.yaml
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r"(helm\.sh/chart:\s*smarter-)\d+\.\d+\.\d+",
        f"\\g<1>{new_version}",
    )

    # Update --version flag in Quickstart section of helm/charts/smarter/README.md
    update_version_in_file(
        "helm/charts/smarter/README.md",
        r"(^\s*--version\s+)(\d+\.\d+\.\d+)(\s*\\)",
        f"\\g<1>{new_version}\\g<3>",
    )

    print(f"Updated helm/charts/smarter/Chart.yaml to {new_version}")


if __name__ == "__main__":
    main()
