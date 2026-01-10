# pylint: disable=W0613
"""Api utils"""

import logging
import os
from typing import Optional
from urllib.parse import urljoin

import httpx
from django.urls import reverse

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
)
from smarter.lib import json
from smarter.lib.drf.models import SmarterAuthToken


logger = logging.getLogger(__name__)


HERE = os.path.abspath(os.path.dirname(__file__))


def apply_manifest(
    filespec: Optional[str] = None,
    manifest: Optional[str] = None,
    username: Optional[str] = None,
    verbose: bool = False,
) -> bool:
    """
    Prepare and get a response from the api/v1/cli/apply endpoint. We need to
    be mindful of the environment we are in, as the
    endpoint may be hosted over https or http.

    Utility for running ``api/v1/cli/`` endpoints to verify their functionality.

    This management command serves both as a utility and an instructional tool
    for interacting with Smarter manifests via the API.
    It is designed to help developers and administrators understand and validate
    the process of applying manifests through the CLI endpoint.

    **Key Features and Demonstrations:**

    - Shows how to generate an API key for a user, which is required for authenticated requests.
    - Demonstrates how to include the API key in HTTP requests to ``api/v1/cli/`` endpoints.
    - Explains how to construct and send HTTP requests to the manifest application endpoint.
    - Illustrates how to handle and interpret the response object returned by the API.

    **Usage:**

    This command can be invoked via Django's ``manage.py`` interface. It
    accepts either a manifest file (YAML or JSON) or a manifest string
    directly, along with the username of the admin user who will
    apply the manifest. The command will:

    1. Validate the provided manifest input.
    2. Retrieve the specified user and ensure they have an associated admin profile.
    3. Generate a single-use API token for authentication.
    4. Construct the appropriate API endpoint URL, considering the current environment (HTTP/HTTPS).
    5. Send the manifest data to the API endpoint using an authenticated HTTP POST request.
    6. Display formatted output, including request details and the API response, with optional verbosity.

    **Error Handling:**

    The command provides clear error messages for common failure scenarios,
    such as missing user profiles, invalid manifest input, or unsuccessful
      responses. All failures are reported with context to aid troubleshooting.

    **Intended Audience:**

    This tool is intended for developers, system administrators, and anyone
    interested in learning how Smarter manifests are applied programmatically.
    It is especially useful for instructional purposes, demonstrations,
    and manual verification of API endpoint behavior.

    .. seealso::

        - :py:class:`smarter.apps.api.v1.cli.urls.ApiV1CliReverseViews`
        - :py:class:`smarter.lib.drf.models.SmarterAuthToken`

    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
    from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError

    user: Optional[User] = None
    data: Optional[str] = None
    logger_prefix = formatted_text("smarter.apps.api.utils.apply_manifest()")

    logger.debug(
        "%s apply_manifest() called with filespec=%s, manifest=%s, username=%s, verbose=%s",
        logger_prefix,
        filespec,
        manifest,
        username,
        verbose,
    )

    if manifest:
        logger.debug("%s Using manifest provided in manifest argument.", logger_prefix)
        data = manifest
    elif filespec:
        try:
            with open(filespec, encoding="utf-8") as file:
                data = file.read()
            logger.debug("%s Using manifest from file: %s", logger_prefix, filespec)
        except FileNotFoundError as e:
            raise SmarterValueError(f"File not found: {filespec}") from e
    if not data:
        raise SmarterValueError("Provide either a filespec or a manifest.")

    if not isinstance(username, str) or not username.strip():
        logger.error("%s Invalid username provided: %s", logger_prefix, username)
        return False

    try:
        user = User.objects.get(username=username.strip())
    except User.DoesNotExist:
        logger.error("%s User with username '%s' does not exist.", logger_prefix, username)
        return False

    user_profile = get_cached_user_profile(user=user)
    if not isinstance(user_profile, UserProfile):
        logger.error("%s No UserProfile found for user '%s'.", logger_prefix, username)
        return False

    user = user_profile.user

    try:
        token_record, token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
            name="apply_manifest",
            user=user,
            description="DELETE ME: single-use key created by smarter.apps.api.utils.apply_manifest()",
        )
        logger.debug("%s Created single-use API token for user '%s'.", logger_prefix, user.username)
    # pylint: disable=W0718
    except Exception:
        return False

    path = reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply, kwargs={})
    url = urljoin(smarter_settings.environment_url, path)
    headers = {"Authorization": f"Token {token_key}", "Content-Type": "application/json"}

    logger.debug(
        "%s - Applying manifest via api endpoint %s as user %s (verbose=%s)",
        logger_prefix,
        url,
        user.username,
        verbose,
    )
    if verbose:
        logger.debug("%s manifest: %s", logger_prefix, data)
        logger.debug("%s headers: %s", logger_prefix, headers)

    httpx_response = httpx.post(url, content=data, headers=headers, timeout=60.0)
    token_record.delete()
    if httpx_response.status_code == httpx.codes.OK:
        logger.debug("%s Manifest applied.", logger_prefix)
    else:
        logger.error("%s Manifest apply failed. Response was %s", logger_prefix, httpx_response.status_code)
        return False

    # wrap up the request
    try:
        response_content = httpx_response.content.decode("utf-8")
    # pylint: disable=W0718
    except Exception:
        logger.error("%s Unable to decode response content.", logger_prefix)
        response_content = httpx_response.content

    if isinstance(response_content, (str, bytearray, bytes)):
        try:
            response_json = json.loads(response_content)
        except json.JSONDecodeError:
            response_json = {"error": "unable to decode response content", "raw": response_content}
    else:
        response_json = {"error": "unable to decode response content"}

    response = json.dumps(response_json) + "\n"
    if verbose:
        if httpx_response.status_code == httpx.codes.OK:
            logger.debug("%s %s", logger_prefix, formatted_text_green(response))
            return True

        msg = f"Manifest apply to {url} failed with status code: {httpx_response.status_code}\nmanifest: {data}\nresponse: {response}"
        raise APIV1CLIViewError(msg)
    return True
