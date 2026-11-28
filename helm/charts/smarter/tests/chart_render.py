"""
Render the smarter chart with ``helm template``, and read what it renders, for the tests that need the real output.

The chart is rendered from a copy without its subcharts (Chart.yaml's dependencies), which ``helm template`` would
otherwise have to download, and with a valid version in place of the placeholder that the release sets. The
Kubernetes Secrets that the chart reads from the cluster don't exist in ``helm template``.

The helpers read the rendered YAML with regular expressions, because the chart's tests use only the standard
library: they rely on the shapes that the templates render, e.g. a document's ``kind:`` at the top level.

The tests that use it need helm, and are skipped without it, except on GitHub Actions, whose runners have it:
``needs_helm`` decorates them.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable, Optional

CHART_PATH = Path(__file__).resolve().parent.parent
APP_NAME = "smarter"
NAMESPACE = "smarter-test"
HELM = shutil.which("helm")


def needs_helm(test_class: type) -> type:
    """Skip a test class without helm, except on GitHub Actions, where its setUpClass then fails with why."""
    skip: Callable[[type], type] = unittest.skipUnless(HELM or os.environ.get("GITHUB_ACTIONS"), "helm isn't installed")
    return skip(test_class)


def require_helm() -> str:
    """Return helm's path, or fail: GitHub Actions' runners have it."""
    if HELM is None:
        raise AssertionError("helm isn't installed, and GitHub Actions' runners have it.")
    return HELM


def render(values: dict[str, Any]) -> list[str]:
    """
    Render the chart with these values.

    :param values: Values, e.g. ``{"env": {...}}``, over values.yaml.
    :returns: The rendered documents.
    """
    helm = require_helm()
    with tempfile.TemporaryDirectory() as folder:
        chart = Path(folder) / APP_NAME
        shutil.copytree(CHART_PATH, chart, ignore=shutil.ignore_patterns("charts", "tests", "__pycache__", "*.lock"))
        chart_yaml = (chart / "Chart.yaml").read_text(encoding="utf-8")
        chart_yaml = re.sub(r"^(version|appVersion): .*$", r"\1: 0.0.1", chart_yaml, flags=re.MULTILINE)
        chart_yaml = chart_yaml[: chart_yaml.index("dependencies:")]
        (chart / "Chart.yaml").write_text(chart_yaml, encoding="utf-8")
        # JSON is YAML: a values file without quoting rules to get wrong.
        values_path = Path(folder) / "values.json"
        values_path.write_text(json.dumps(values), encoding="utf-8")
        command = [helm, "template", APP_NAME, str(chart), "--namespace", NAMESPACE, "-f", str(values_path)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)  # nosec B603
    if completed.returncode != 0:
        raise AssertionError(f"helm template failed:\n{completed.stderr}")
    return completed.stdout.split("\n---\n")


def kind_and_name(document: str) -> tuple[str, str]:
    """A rendered document's kind and name, its metadata's name wherever it is in the block, or empty strings."""
    kind = re.search(r"^kind: (\w+)$", document, re.MULTILINE)
    if kind is None or "\nmetadata:\n" not in document:
        return "", ""
    metadata = document.split("\nmetadata:\n", 1)[1]
    for line in metadata.splitlines():
        if not line.startswith(" "):
            break
        name = re.match(r'^  name: "?([^"\n]+?)"?$', line)
        if name is not None:
            return kind.group(1), name.group(1)
    return "", ""


def documents_of_kind(documents: list[str], *kinds: str) -> dict[str, str]:
    """The rendered documents of these kinds, by name."""
    retval = {}
    for document in documents:
        kind, name = kind_and_name(document)
        if kind in kinds:
            retval[name] = document
    return retval


def workloads(documents: list[str]) -> dict[str, str]:
    """Each rendered Deployment, Job and CronJob, by name."""
    return documents_of_kind(documents, "Deployment", "Job", "CronJob")


def service_type(document: str) -> Optional[str]:
    """The kind of pod that a workload's SERVICE_TYPE names, or None if it sets none, or more than one."""
    values = set(re.findall(r"- name: SERVICE_TYPE\n\s+value: \"?([a-z-]+)\"?", document))
    if len(values) != 1:
        return None
    return values.pop()


def rules(document: str) -> list[dict[str, list[str]]]:
    """
    A Role's or ClusterRole's rules, as toYaml renders them: each rule's lists, by key.

    :param document: The rendered Role.
    :returns: e.g. ``[{"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list"]}]``.
    """
    retval: list[dict[str, list[str]]] = []
    if "\nrules:\n" not in document:
        return retval
    key = ""
    for line in document.split("\nrules:\n", 1)[1].splitlines():
        if not line.startswith(" "):
            break
        rule_start = re.match(r"^  - (\w+):$", line)
        key_line = re.match(r"^    (\w+):$", line)
        item = re.match(r'^    - "?([^"]*)"?$', line)
        if rule_start is not None:
            key = rule_start.group(1)
            retval.append({key: []})
        elif key_line is not None:
            key = key_line.group(1)
            retval[-1][key] = []
        elif item is not None:
            retval[-1][key].append(item.group(1))
    return retval
