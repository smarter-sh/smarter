# pylint: disable=W0613
"""Api utils."""

import os
from typing import Optional

import yaml
from django.test import RequestFactory

from smarter.apps.account.models import User, UserProfile
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.parsing import parse_manifest

logger = logging.getSmarterLogger(__name__)


HERE = os.path.abspath(os.path.dirname(__file__))


def loggable_manifest(manifest: Optional[str]) -> Optional[str]:
    """
    Return a manifest as a log message may show it: a Secret manifest is replaced by a placeholder.

    A Secret manifest's ``spec.config.value`` is the secret's unencrypted value.

    :param manifest: The manifest, as YAML or JSON text.
    :returns: The manifest, or a placeholder for a Secret manifest or one that isn't valid YAML.
    """
    if not manifest:
        return manifest
    try:
        documents = list(yaml.safe_load_all(manifest))
    except yaml.YAMLError:
        return f"<a manifest of {len(manifest)} characters that is not valid YAML, not logged>"
    for doc in documents:
        if isinstance(doc, dict) and doc.get("kind") == SAMKinds.SECRET.value:
            name = (doc.get("metadata") or {}).get("name")
            return f"<{SAMKinds.SECRET.value} manifest {name}, not logged>"
    return manifest


def apply_manifest(
    filespec: Optional[str] = None,
    manifest: Optional[str] = None,
    username: Optional[str] = None,
    verbose: bool = False,
) -> bool:
    """
    Apply a manifest as a user, with its kind's broker, in this process.

    It is what ``smarter apply`` does through the cli api, without the request: no api key, and no connection to the
    platform's own url. An earlier version posted the manifest to the cli api over HTTP, a request outside the tool
    runner and ``safe_http`` that nothing in the platform needed (ADR-038, issue #1082).

    :param filespec: A file that holds the manifest.
    :param manifest: The manifest, as YAML or JSON text, instead of a file.
    :param username: The user who applies it.
    :param verbose: Log the manifest, and the broker's response.
    :returns: True if the broker applied it; False for a missing user or profile, an unknown kind, or no response.
    :raises SmarterValueError: If neither a manifest nor a readable file is given.
    :raises Exception: If the broker answers with a status other than 200.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError

    user: Optional[User] = None
    data: Optional[str] = None

    logger.debug(
        "called with filespec=%s, manifest=%s, username=%s, verbose=%s",
        filespec,
        loggable_manifest(manifest),
        username,
        verbose,
    )

    if manifest:
        logger.debug("Using manifest provided in manifest argument.")
        data = manifest
    elif filespec:
        try:
            with open(filespec, encoding="utf-8") as file:
                data = file.read()
            logger.debug("Using manifest from file: %s", filespec)
        except FileNotFoundError as e:
            raise SmarterValueError(f"File not found: {filespec}") from e
    if not data:
        raise SmarterValueError("Provide either a filespec or a manifest.")

    if not isinstance(username, str) or not username.strip():
        logger.error("Invalid username provided: %s", username)
        return False

    try:
        user = User.objects.get(username=username.strip())
    except User.DoesNotExist:
        logger.error("User with username '%s' does not exist.", username)
        return False

    user_profile = UserProfile.get_cached_object(user=user)
    if not isinstance(user_profile, UserProfile):
        logger.error("No UserProfile found for user '%s'.", username)
        return False

    user = user_profile.cached_user

    if verbose:
        logger.debug("manifest: %s", loggable_manifest(data))

    parsed_manifest = parse_manifest(data)
    factory = RequestFactory()
    fake_request = factory.post("/fake-url/", data=parsed_manifest, content_type="application/json")
    fake_request.user = user_profile.user

    kind = parsed_manifest.get("kind")
    if not isinstance(kind, str):
        return False
    BrokerClass = Brokers.get_broker(kind)
    if BrokerClass is None or not issubclass(BrokerClass, AbstractBroker):
        return False

    broker = BrokerClass(request=fake_request, manifest=parsed_manifest, user_profile=user_profile)
    response_content = broker.apply(request=fake_request)
    if response_content is None:
        logger.error("returned None")
        return False

    if response_content.status_code == 200:
        logger.debug("manifest applied successfully")
    else:
        logger.error("manifest: %s", loggable_manifest(data))
        logger.error("response: %s", response_content.content)
        msg = f"Manifest apply failed with status code: {response_content.status_code}\nmanifest: {loggable_manifest(data)}\nresponse: {response_content.content!r}"
        # pylint: disable=W0719
        raise Exception(msg)

    if isinstance(response_content, (str, bytearray, bytes)):
        try:
            response_json = json.loads(response_content)
        except json.JSONDecodeError:
            response_json = {"error": "unable to decode response content", "raw": response_content}
    else:
        response_json = {"error": "unable to decode response content"}

    response = json.dumps(response_json) + "\n"
    if verbose:
        if response_content.status_code == 200:
            logger.debug(
                "%s",
                logging.SmarterFormattedText.text(response, logging.SmarterFormattedText.BRIGHT_GREEN),
            )
            return True

        msg = f"Manifest apply failed with status code: {response_content.status_code}\nmanifest: {loggable_manifest(data)}\nresponse: {response}"
        raise APIV1CLIViewError(msg)
    return True
