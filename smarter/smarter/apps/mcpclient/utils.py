"""MCPClient utils."""

import io
import os
import re
from pathlib import Path
from typing import Optional, Union

import yaml
from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.secret.models import Secret
from smarter.common.const import PYTHON_ROOT
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


class MCPClientExample:
    """
    A class for loading and working with built-in YAML-based MCPClient examples.

    This class reads MCPClient example files in YAML format, parses their contents, and exposes metadata and serialization methods for inspection and testing.

    :param filepath: The directory path containing the YAML file.
    :type filepath: str
    :param filename: The name of the YAML file to load.
    :type filename: str

    .. seealso::

        :class:`MCPClientExamples` for managing collections of MCPClient examples.

    **Example usage**::

        example = MCPClientExample(filepath="/path/to/examples", filename="deepwiki.yaml")
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
        """Return the name of the MCPClient manifest."""
        return self._filename

    @property
    def filepath(self) -> Optional[str]:
        """Return the filepath of the MCPClient manifest."""
        return self._filepath

    @property
    def fullpath(self) -> Optional[str]:
        return str(Path(self.filepath) / self.filename) if self.filepath and self.filename else None

    @property
    def name(self) -> Optional[str]:
        """Return the name of the MCPClient."""
        try:
            retval = self._json["metadata"]["name"] if isinstance(self._json, dict) else None
        except KeyError:
            logger.warning("MCPClientExample: %s is malformed and has no metadata.name", self.filename)
            retval = self.convert_filename()
        return retval

    @property
    def credentials(self) -> Optional[str]:
        """Return the name of the Secret in ``spec.config.credentials``, or ``None`` if there isn't one."""
        try:
            return self._json["spec"]["config"].get("credentials") if isinstance(self._json, dict) else None
        except (KeyError, AttributeError):
            return None

    def to_yaml(self) -> Optional[str]:
        """Return the MCPClient as a yaml string."""
        return self._yaml

    def to_json(self) -> Optional[Union[dict, list]]:
        """Return the MCPClient as a dictionary."""
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
            logger.error("MCPClientExample: %s failed to convert filename: %s", self.filename, e)
            return self.filename


class MCPClientExamples:
    """
    A class for managing a collection of :class:`MCPClientExample` instances.

    This class loads all YAML-based MCPClient examples from a specified directory, providing access to the collection and utility methods for counting and retrieving examples.

    :param args: Optional positional arguments (unused).
    :type args: tuple
    :param kwargs: Optional keyword arguments (unused).
    :type kwargs: dict

    .. note::

        Only files ending with ``.yaml`` in the mcpclients path are loaded as examples.

    .. tip::

        Use :meth:`count` to get the number of loaded MCPClient examples, and the :meth:`mcpclients` property to access the list.

    .. seealso::

        :class:`MCPClientExample` for individual example details.

    **Example usage**::

        examples = MCPClientExamples()
        print(examples.count())
        for example in examples.mcpclients:
            print(example.filename, example.name)
    """

    _mcpclient_examples: list[MCPClientExample] = []
    MCPCLIENTS_PATH = os.path.join(PYTHON_ROOT, "smarter", "apps", "mcpclient", "data", "mcpclients")

    # pylint: disable=W0613
    def __init__(self, *args, **kwargs):
        """Initialize the class."""
        self._mcpclient_examples = []
        for file in sorted(os.listdir(self.MCPCLIENTS_PATH)):
            if file.endswith(".yaml"):
                mcpclient_example = MCPClientExample(filepath=self.MCPCLIENTS_PATH, filename=file)
                self._mcpclient_examples.append(mcpclient_example)

    def count(self) -> int:
        """Return the number of MCPClients."""
        return len(self._mcpclient_examples)

    @property
    def mcpclients(self) -> list[MCPClientExample]:
        """Return a list of MCPClient examples."""
        return self._mcpclient_examples


def add_builtin_mcpclients(user_profile: Optional[UserProfile], verbose: bool = False) -> bool:
    """
    Apply the built-in MCPClient manifests, in ``data/mcpclients``, for a user.

    ``manage.py initialize_platform`` applies them for the Smarter admin user, so that every
    account's LLMClients may list them in their ``spec.mcpClients``.

    :param user_profile: The `UserProfile` instance that will own the MCPClients. Must not be `None`.
    :type user_profile: Optional[UserProfile]
    :param verbose: If True, print the output of each ``apply_manifest`` call.
    :type verbose: bool

    :return: Returns `True` if every MCPClient manifest was applied or skipped, `False` if any of them failed.
    :rtype: bool

    :raises SmarterValueError: If `user_profile` is not provided.

    .. note::

        - This function applies the manifests with the ``apply_manifest`` management command.
        - Manifests that require authentication name a Smarter Secret in ``spec.config.credentials``,
          and the MCPClient broker refuses to apply them until that Secret exists. Those manifests
          are skipped until the Secret is created, after which re-running this function applies them.
        - A manifest that fails to apply is logged and skipped, so that one bad manifest does
          not prevent the others from being applied.

    .. seealso::

        - :class:`MCPClientExamples`
        - :class:`SmarterValueError`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.account.models import UserProfile
        from smarter.apps.mcpclient.utils import add_builtin_mcpclients

        user_profile = UserProfile.objects.get(user__username="newuser")
        success = add_builtin_mcpclients(user_profile)
        if success:
            print("Built-in MCPClients created successfully.")
    """
    logger_prefix = formatted_text(f"{__name__}.add_builtin_mcpclients()")
    logger.debug("%s Adding built-in MCPClients for user profile: %s", logger_prefix, user_profile)

    mcpclient_examples = MCPClientExamples()
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add built-in MCPClients.")
    username: str = user_profile.user.username
    retval = True

    def secret_exists(name: str) -> bool:
        # the same lookup as SAMMCPClientBroker.resolve_secret()
        if Secret.objects.filter(name=name, user_profile=user_profile).exists():
            return True
        return (
            Secret.objects.filter(name=name)
            .with_read_permission_for(user_profile.user)  # type: ignore[attr-defined]
            .exists()
        )

    for mcpclient in mcpclient_examples.mcpclients:
        if mcpclient.credentials and not secret_exists(mcpclient.credentials):
            logger.info(
                "%s skipping MCPClient %s because Secret %s does not exist.",
                logger_prefix,
                mcpclient.name,
                mcpclient.credentials,
            )
            if verbose:
                print(f"Skipped manifest {mcpclient.fullpath}: Secret {mcpclient.credentials} does not exist.")
            continue
        output = io.StringIO()
        error_output = io.StringIO()
        try:
            call_command(
                "apply_manifest", filespec=mcpclient.fullpath, username=username, stdout=output, stderr=error_output
            )
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s failed to apply MCPClient manifest %s: %s", logger_prefix, mcpclient.fullpath, e)
            retval = False
            continue
        if error_output.getvalue():
            print(f"Applied manifest {mcpclient.fullpath} with warnings: {error_output.getvalue()}")
        elif verbose:
            print(f"Applied manifest {mcpclient.fullpath}. output: {output.getvalue()}")
    return retval
