"""
Tests of the Dockerfile's manage.py steps, which load Django's settings while the image is built.

Outside the local environment, the settings refuse to load without DJANGO_SECRET_KEY or Redis's password,
SMARTER_SUBSYSTEM_REDIS_PASSWORD, and CI builds the prod image. A build step that runs manage.py without a
throwaway value for each stops the build. The local build that make docker-test runs can't show it: there,
the settings have defaults for both.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import re
import unittest
from pathlib import Path

DOCKERFILE_PATH = Path(__file__).resolve().parent.parent.parent / "Dockerfile"

BUILD_TIME_SETTINGS = ("DJANGO_SECRET_KEY", "SMARTER_SUBSYSTEM_REDIS_PASSWORD")
"""The settings that a non-local environment requires, which each manage.py step must set for itself."""


def run_instructions(text: str) -> list[str]:
    """
    Return the Dockerfile's RUN instructions, each with its continuation lines joined.

    :param text: The Dockerfile.
    :returns: Each RUN instruction, as one line.
    """
    instructions = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not current and not stripped.startswith("RUN "):
            continue
        current.append(stripped.rstrip("\\").strip())
        if not stripped.endswith("\\"):
            instructions.append(" ".join(current))
            current = []
    return instructions


def manage_py_steps(text: str) -> list[str]:
    """
    Return the RUN instructions that run manage.py.

    :param text: The Dockerfile.
    :returns: Those instructions.
    """
    steps = []
    for instruction in run_instructions(text):
        if re.search(r"\bpython manage\.py\b", instruction):
            steps.append(instruction)
    return steps


class TestDockerfileBuildSettings(unittest.TestCase):
    """Every manage.py step of the build sets the settings that a non-local environment requires."""

    def test_finds_the_steps(self):
        """Compilemessages and collectstatic both load the settings."""
        steps = manage_py_steps(DOCKERFILE_PATH.read_text(encoding="utf-8"))
        commands = " ".join(steps)
        self.assertIn("manage.py compilemessages", commands)
        self.assertIn("manage.py collectstatic", commands)

    def test_each_step_sets_a_throwaway_value_for_each_setting(self):
        """Each value is generated in the step itself, so that it is never written to the image."""
        for step in manage_py_steps(DOCKERFILE_PATH.read_text(encoding="utf-8")):
            for setting in BUILD_TIME_SETTINGS:
                with self.subTest(step=step[:60], setting=setting):
                    self.assertRegex(step, rf'{setting}="\$\(python -c \'import secrets; print\(secrets\.')

    def test_no_setting_is_an_image_wide_env(self):
        """An ENV or ARG would write the value into the image's configuration, where anyone with the image reads it."""
        text = DOCKERFILE_PATH.read_text(encoding="utf-8")
        for setting in BUILD_TIME_SETTINGS:
            with self.subTest(setting=setting):
                self.assertNotRegex(text, rf"(?m)^\s*(ENV|ARG)\s+{setting}\b")


if __name__ == "__main__":
    unittest.main()
