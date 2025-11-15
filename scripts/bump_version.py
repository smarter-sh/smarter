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
"""

import re
import sys
from pathlib import Path


def update_version_in_file(filepath, pattern, replacement):
    path = Path(filepath)
    text = path.read_text(encoding="utf-8")
    new_text = re.sub(pattern, replacement, text)
    path.write_text(new_text, encoding="utf-8")


def bump_helm_chart_patch_version():
    """
    Update the version and annotations.helm.sh/chart in Helm helm/Chart.yaml

    Note that the Helm version is logically "detached" from the application version,
    so for simplicity, we always only tick the patch version here. Anything more
    complex should be handled manually.

    example values:
        version: 0.7.5
        annotations:
          "helm.sh/chart": "smarter-0.7.5"
    """
    path = Path("helm/charts/smarter/Chart.yaml")
    text = path.read_text(encoding="utf-8")
    version_match = re.search(r"version:\s*(\d+)\.(\d+)\.(\d+)", text)
    if not version_match:
        print("Error: Could not find version in helm/charts/smarter/Chart.yaml")
        sys.exit(1)
    major, minor, patch = map(int, version_match.groups())
    patch += 1  # Bump patch version
    new_version = f"{major}.{minor}.{patch}"
    new_text = re.sub(r"version:\s*\d+\.\d+\.\d+", f"version: {new_version}", text)
    new_text = re.sub(
        r'helm\.sh/chart":\s*"smarter-\d+\.\d+\.\d+"', f'helm.sh/chart": "smarter-{new_version}"', new_text
    )
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

    # Update pyproject.toml
    update_version_in_file("pyproject.toml", r'version\s*=\s*["\'].*?["\']', f'version = "{new_version}"')

    # Update Dockerfile (example: ARG VERSION=...)
    update_version_in_file(
        "Dockerfile",
        r'org\.opencontainers\.image\.version="[^"]+"',
        f'org.opencontainers.image.version="{new_version}"',
    )

    print(
        f"Version updated to {new_version} in __version__.py, pyproject.toml, Dockerfile and helm/charts/smarter/Chart.yaml"
    )

    # Update Helm chart
    update_version_in_file(
        "helm/charts/smarter/Chart.yaml",
        r'appVersion:\s*["\']?[\w\.\-]+["\']?',
        f"appVersion: {new_version}",
    )

    bump_helm_chart_patch_version()


if __name__ == "__main__":
    main()
