"""Guardrails utils."""

import io
import os
import re
from typing import Optional, Union

import yaml
from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.common.const import PYTHON_ROOT
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.GUARDRAIL_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class GuardrailExample:
    """
    A class for loading and working with built-in YAML-based guardrail examples.

    This class reads guardrail example files in YAML format, parses their contents, and exposes metadata and serialization methods for inspection and testing.

    :param filepath: The directory path containing the YAML file.
    :type filepath: str
    :param filename: The name of the YAML file to load.
    :type filename: str

    .. seealso::

        :class:`GuardrailExamples` for managing collections of guardrail examples.

    **Example usage**::

        example = GuardrailExample(filepath="/path/to/examples", filename="my_guardrail.yaml")
        print(example.name)
        print(example.to_yaml())
        print(example.to_json())
    """

    _filename: Optional[str]
    _filepath: Optional[str]
    _json: Optional[Union[list, dict]]
    _yaml: Optional[str]

    def __init__(self, filepath: str, filename: str):
        """Initialize the class from a yaml file."""
        with open(os.path.join(filepath, filename), encoding="utf-8") as file:
            self._yaml = file.read()
            self._json = yaml.safe_load(self._yaml)

        self._filename = filename
        self._filepath = filepath

    @property
    def filename(self) -> Optional[str]:
        """Return the name of the guardrail manifest."""
        return self._filename

    @property
    def filepath(self) -> Optional[str]:
        """Return the filepath of the guardrail manifest."""
        return self._filepath

    @property
    def fullpath(self) -> Optional[str]:
        if not self.filename:
            return None
        if not self.filepath:
            return None
        return self.filepath + self.filename

    @property
    def name(self) -> Optional[str]:
        """Return the name of the guardrail."""
        try:
            retval = self._json["metadata"]["name"] if isinstance(self._json, dict) else None
        except KeyError:
            logger.warning("GuardrailExample: %d is malformed and has no metadata.name", self.filename)
            retval = self.convert_filename()
        return retval

    def to_yaml(self) -> Optional[str]:
        """Return the guardrail as a yaml string."""
        return self._yaml

    # TODO: this fails on Guardrail.create() due to missing tags
    # django.core.exceptions.ValidationError: ["Invalid data: missing meta_data['tags']"]
    def to_json(self) -> Optional[Union[dict, list]]:
        """Return the guardrail as a dictionary."""
        return self._json

    def convert_filename(self) -> Optional[str]:
        """Convert the filename to the desired format."""
        if not isinstance(self.filename, str):
            return self.filename
        try:
            filename = os.path.splitext(self.filename)[0]  # Remove the file extension
            name = re.sub(r"[-_]", " ", filename)  # Replace hyphens and underscores with spaces
            name = name.title().replace(" ", "")  # Capitalize each word and remove spaces
            return name
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("GuardrailExample: %s failed to convert filename: %s", self.filename, e)
            return self.filename


class GuardrailExamples:
    """
    A class for managing a collection of :class:`GuardrailExample` instances.

    This class loads all YAML-based guardrail examples from a specified directory, providing access to the collection and utility methods for counting and retrieving examples.

    :param args: Optional positional arguments (unused).
    :type args: tuple
    :param kwargs: Optional keyword arguments (unused).
    :type kwargs: dict

    .. note::

        Only files ending with ``.yaml`` in the guardrails path are loaded as examples.

    .. tip::

        Use :meth:`count` to get the number of loaded guardrail examples, and the :meth:`guardrails` property to access the list.

    .. seealso::

        :class:`GuardrailExample` for individual example details.

    **Example usage**::

        examples = GuardrailExamples()
        print(examples.count())
        for example in examples.guardrails:
            print(example.filename, example.name)
    """

    _guardrail_examples: list[GuardrailExample] = []
    HERE = os.path.abspath(os.path.dirname(__file__))
    PLUGINS_PATH = os.path.join(PYTHON_ROOT, "smarter", "apps", "guardrail", "data", "guardrails")

    def __init__(self, *args, **kwargs):
        """Initialize the class."""
        self._guardrail_examples = []
        for file in os.listdir(self.PLUGINS_PATH):
            if file.endswith(".yaml"):
                guardrail_example = GuardrailExample(filepath=self.PLUGINS_PATH, filename=file)
                self._guardrail_examples.append(guardrail_example)

    def count(self) -> int:
        """Return the number of guardrails."""
        return len(self._guardrail_examples)

    @property
    def guardrails(self) -> list[GuardrailExample]:
        """Return a list of guardrails in dictionary format."""
        return self._guardrail_examples


# pylint: disable=W0613,C0415
def add_builtin_guardrails(user_profile: Optional[UserProfile], verbose: bool = False) -> bool:
    """
    Create example guardrails for a new user.

    This function provisions example guardrails for a user.

    :param user_profile: The `UserProfile` instance representing the new user. Must not be `None`.
    :type user_profile: Optional[UserProfile]

    :return: Returns `True` if all example guardrails are created and validated successfully.
    :rtype: bool

    :raises SmarterValueError: If `user_profile` is not provided, or if manifest/secret application fails,
        or if a guardrail does not have a valid YAML representation.

    .. note::

        - This function applies sample secrets and connections using Django management commands. Manifests for these are located in smarter/apps/guardrail/data.
        - This function is called during deployment jobs.

    .. important::

        - The `user_profile` parameter must be a valid `UserProfile` instance. Passing `None` or an incorrect type will result in an error.
        - If any manifest or secret update fails, the function raises an exception and does not proceed with guardrail creation.

    .. seealso::

        - :class:`GuardrailExamples`
        - :class:`GuardrailController`
        - :class:`SmarterValueError`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.account.models import UserProfile
        from smarter.apps.guardrail.utils import add_example_guardrails

        user_profile = UserProfile.objects.get(user__username="newuser")
        success = add_example_guardrails(user_profile)
        if success:
            print("Example guardrails created successfully.")
    """
    # pylint: disable=W0621
    logger_prefix = formatted_text(f"{__name__}.add_example_guardrails()")
    logger.debug(
        "%s.add_example_guardrails Adding example guardrails for user profile: %s", logger_prefix, user_profile
    )

    guardrail_examples = GuardrailExamples()
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add example guardrails.")
    username: str = user_profile.user.username
    output = io.StringIO()
    error_output = io.StringIO()

    def apply(file_path):

        call_command("apply_manifest", filespec=file_path, username=username, stdout=output, stderr=error_output)
        if error_output.getvalue():
            print(f"Command completed with warnings: {error_output.getvalue()}")
        else:
            print(f"Applied manifest {file_path}. output: {output.getvalue()}")

    for guardrail in guardrail_examples.guardrails:
        apply(guardrail.fullpath)
    return True
