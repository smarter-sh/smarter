# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings of third-party services that the platform integrates with."""

import warnings
from typing import Optional

from pydantic import BaseModel, Field, SecretStr

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import before_field_validator
from smarter.common.exceptions import SmarterConfigurationError


class IntegrationSettings(BaseModel):
    """The credentials of third-party services: Account Manager, GitHub, Slack, Stripe and social login."""

    account_manager_api_key: Optional[SecretStr] = Field(
        settings_defaults.ACCOUNT_MANAGER_API_KEY,
        description="The platform's key for Account Manager's subscription status api, which multitenant authentication sends as 'Authorization: Platform <key>'. Masked by pydantic SecretStr.",
        examples=["the key that Account Manager's create_platform_api_key command printed"],
        title="Account Manager API Key",
    )
    """
    The platform's key for Account Manager's subscription status api.

    A multitenant platform asks Account Manager, when a user signs in, whether the user has an
    active subscription (see :py:mod:`smarter.lib.social_core.backends.multitenant`). The key
    identifies the platform to Account Manager, which issues one per platform with its
    ``create_platform_api_key`` management command. It is sent only to Account Manager, as
    ``Authorization: Platform <key>``.

    Without a key, the platform asks without one, which Account Manager answers until its
    ``require_platform_key`` waffle switch is on.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.ACCOUNT_MANAGER_API_KEY``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("account_manager_api_key")
    def validate_account_manager_api_key(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `account_manager_api_key` field.

        Args:
            v (Optional[SecretStr]): The key to validate.
        Returns:
            Optional[SecretStr]: The validated key, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.ACCOUNT_MANAGER_API_KEY
        if is_missing_value(v):
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"account_manager_api_key of type {type(v)} is not a SecretStr")
        return v

    github_token: Optional[SecretStr] = Field(
        settings_defaults.GITHUB_TOKEN,
        description="The platform's GitHub token, from GITHUB_TOKEN, for the GitHub REST api requests that retrieve remote SkillPlugin skills, and that open the bug reports of the platform's staff. Masked by pydantic SecretStr.",
        examples=["ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"],
        title="GitHub Token",
    )
    """
    The platform's GitHub token, from ``GITHUB_TOKEN``.

    It is read from the first of ``GITHUB_TOKEN``, ``GH_TOKEN`` and ``GITHUB_API_TOKEN`` that is set,
    each with or without the ``SMARTER_`` prefix (see
    :data:`~smarter.common.conf.defaults.GITHUB_TOKEN_NAMES`). It is used for two things:

    - **SkillPlugin skills.** A SkillPlugin whose skill is in a GitHub repository lists the skill's
      files with the GitHub git trees api. Without a token those requests are anonymous, and GitHub
      limits them to 60 per hour per client IP address, which hosts that share an address, such as
      GitHub Actions runners, reach quickly. Any token raises the limit, with no scopes: in GitHub
      Actions, the workflow's own ``GITHUB_TOKEN`` will do. See
      :py:func:`smarter.apps.llmtool.plugin.skill_sources.list_github_skill_files`.
    - **Bug reports.** The MCPServer's staff-only tool ``create_bug_report`` opens a GitHub issue in a
      repository of The Smarter Project with it, when Smarter Sysadmin has diagnosed a bug and the
      staff member agrees to report it. For that, it must be a classic personal access token,
      ``ghp_...``, with the ``public_repo`` scope, and the issue is written as its owner. See
      :py:func:`smarter.apps.mcpserver.services.github.bug_reports.create_bug_report`.

    The token is sent only to ``api.github.com``, and is never logged.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.GITHUB_TOKEN``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("github_token")
    def validate_github_token(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `github_token` field.

        Args:
            v (Optional[SecretStr]): The GitHub token to validate.
        Returns:
            Optional[SecretStr]: The validated GitHub token, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.GITHUB_TOKEN
        if is_missing_value(v):
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"github_token of type {type(v)} is not a SecretStr")
        return v

    social_auth_google_oauth2_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        description="The OAuth2 key for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-key"],
        title="Google OAuth2 Key",
    )
    """
    The OAuth2 key for Google social authentication.

    Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID.
    """

    @before_field_validator("social_auth_google_oauth2_key")
    def validate_social_auth_google_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 key value to validate.
        Returns:
            SecretStr: The validated Google OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
            return settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_key of type {type(v)} is not a SecretStr")
        return v

    social_auth_google_oauth2_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        description="The OAuth2 secret for Google social authentication. Masked by pydantic SecretStr.",
        examples=["your-google-oauth2-secret"],
        title="Google OAuth2 Secret",
    )
    """
    The OAuth2 secret for Google social authentication.

    Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for Google social authentication.
    It is required for enabling users to log in using their Google accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_google_oauth2_secret")
    def validate_social_auth_google_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_google_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The Google OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated Google OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_google_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_github_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GITHUB_KEY,
        description="The OAuth2 key for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-key"],
        title="GitHub OAuth2 Key",
    )
    """
    The OAuth2 key for GitHub social authentication.

    Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GITHUB_KEY``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """

    @before_field_validator("social_auth_github_key")
    def validate_social_auth_github_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_key` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 key value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GITHUB_KEY is not None:
            return settings_defaults.SOCIAL_AUTH_GITHUB_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_key of type {type(v)} is not a SecretStr")

        return v

    social_auth_github_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_GITHUB_SECRET,
        description="The OAuth2 secret for GitHub social authentication. Masked by pydantic SecretStr.",
        examples=["your-github-oauth2-secret"],
        title="GitHub OAuth2 Secret",
    )
    """
    The OAuth2 secret for GitHub social authentication.

    Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for GitHub social authentication.
    It is required for enabling users to log in using their GitHub accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_GITHUB_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_github_secret")
    def validate_social_auth_github_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_github_secret` field.

        Args:
            v (Optional[SecretStr]): The GitHub OAuth2 secret value to validate.
        Returns:
            SecretStr: The validated GitHub OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_GITHUB_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_GITHUB_SECRET

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_github_secret of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_key: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY,
        description="The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-key"],
        title="LinkedIn OAuth2 Key",
    )
    """
    .. deprecated:: 0.13.35.

        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 key for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client ID used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client ID
    """

    @before_field_validator("social_auth_linkedin_oauth2_key")
    def validate_social_auth_linkedin_oauth2_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_key` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 key value to validate.
        Returns:
            SecretStr: The validated LinkedIn OAuth2 key.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY is not None:
            return settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_key of type {type(v)} is not a SecretStr.")
        return v

    social_auth_linkedin_oauth2_secret: SecretStr = Field(
        settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET,
        description="The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.",
        examples=["your-linkedin-oauth2-secret"],
        title="LinkedIn OAuth2 Secret",
    )
    """
    .. deprecated:: 0.13.35.

        This setting is deprecated and will be removed in a future release. LinkedIn social authentication is no longer supported or recommended for new deployments.

    The OAuth2 secret for LinkedIn social authentication. Masked by pydantic SecretStr.
    This setting provides the OAuth2 client secret used for LinkedIn social authentication.
    It was required for enabling users to log in using their LinkedIn accounts.

    :type: SecretStr
    :default: Value from ``settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET``
    :raises SmarterConfigurationError: If the value is not a valid OAuth2 client secret
    """

    @before_field_validator("social_auth_linkedin_oauth2_secret")
    def validate_social_auth_linkedin_oauth2_secret(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `social_auth_linkedin_oauth2_secret` field.

        Args:
            v (Optional[SecretStr]): The LinkedIn OAuth2 secret value to validate.

        Returns:
            SecretStr: The validated LinkedIn OAuth2 secret.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET is not None:
            return settings_defaults.SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"social_auth_linkedin_oauth2_secret of type {type(v)} is not a SecretStr.")
        return v

    slack_bot_token: Optional[SecretStr] = Field(
        settings_defaults.SLACK_BOT_TOKEN,
        description="A Slack app's bot token, xoxb-..., which the platform posts its Kubernetes jobs' logs to Slack with. Masked by pydantic SecretStr.",
        examples=["xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Slack Bot Token",
    )
    """
    A Slack app's bot token, ``xoxb-...``, for the platform's Slack service.

    The Helm chart's init Job and nightly database backup post their outcome, and their log, to a
    Slack channel with it, when the chart's ``databaseInit.notifySlackChannel`` or
    ``databaseScheduledBackup.notifySlackChannel`` names one. The bot needs the scopes
    ``chat:write`` and ``files:write``, and must be a member of the channel. The optional Slack
    bot, the Helm chart's ``slack-bot`` subchart, reads the same token from
    ``SMARTER_SLACK_BOT_TOKEN``.

    The token is sent only to ``slack.com``. See
    :py:class:`smarter.apps.infrastructure.services.slack.SlackWebApiService`.

    :type: Optional[SecretStr]
    :default: Value from ``settings_defaults.SLACK_BOT_TOKEN``, None if it is not set.
    :raises SmarterConfigurationError: If the value is not a SecretStr.
    """

    @before_field_validator("slack_bot_token")
    def validate_slack_bot_token(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
        """Validates the `slack_bot_token` field.

        Args:
            v (Optional[SecretStr]): The Slack bot token to validate.
        Returns:
            Optional[SecretStr]: The validated Slack bot token, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = settings_defaults.SLACK_BOT_TOKEN
        if is_missing_value(v):
            return None

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"slack_bot_token of type {type(v)} is not a SecretStr")
        return v

    stripe_live_secret_key: Optional[SecretStr] = Field(
        settings_defaults.STRIPE_LIVE_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe live environment.",
        examples=["sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Stripe Live Secret Key",
    )
    """
    .. deprecated:: 0.13.0.

        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe live environment.
    This setting provides the secret key used to authenticate with Stripe's live environment.
    It is used for processing real transactions and payments.

    :type: Optional[str]
    :default: Value from ``settings_defaults.STRIPE_LIVE_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("stripe_live_secret_key")
    def validate_stripe_live_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `stripe_live_secret_key` field.

        Args:
            v (Optional[SecretStr]): The Stripe live secret key to validate.
        Returns:
            SecretStr: The validated Stripe live secret key.
        """
        if v is None:
            warnings.warn(
                "The 'stripe_live_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return settings_defaults.STRIPE_LIVE_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_live_secret_key of type {type(v)} is not a SecretStr.")
        return v

    stripe_test_secret_key: Optional[SecretStr] = Field(
        settings_defaults.STRIPE_TEST_SECRET_KEY,
        description="DEPRECATED: The secret key for Stripe test environment.",
        examples=["sk_test_xxxxxxxxxxxxxxxxxxxxxxxx"],
        title="Stripe Test Secret Key",
    )
    """
    .. deprecated:: 0.13.0.

        This setting is deprecated and will be removed in a future release. Please use the new payment processing configuration settings.

    The secret key for Stripe test environment.
    This setting provides the secret key used to authenticate with Stripe's test environment.
    It is used for processing test transactions and payments.

    :type: Optional[str]
    :default: Value from ``settings_defaults.STRIPE_TEST_SECRET_KEY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("stripe_test_secret_key")
    def validate_stripe_test_secret_key(cls, v: Optional[SecretStr]) -> SecretStr:
        """Validates the `stripe_test_secret_key` field.

        Args:
            v (Optional[SecretStr]): The Stripe test secret key to validate.
        Returns:
            SecretStr: The validated Stripe test secret key.
        """
        if v is None:
            warnings.warn(
                "The 'stripe_test_secret_key' field is deprecated and will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            return settings_defaults.STRIPE_TEST_SECRET_KEY

        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError(f"stripe_test_secret_key of type {type(v)} is not a SecretStr.")
        return v


__all__ = ["IntegrationSettings"]
