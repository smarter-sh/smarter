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


if __name__ == "__main__":
    main()
