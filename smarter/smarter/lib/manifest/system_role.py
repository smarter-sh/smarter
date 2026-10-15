"""
The limits of a manifest's system role: an LLMClient's ``defaultSystemRole``, and a plugin's ``systemRole``.

A system role's length is the author's decision, between what the LLM needs to be told and
what each turn costs, so the platform doesn't impose a style. It only rejects a value so long
that it can only be a mistake, e.g. a document pasted into the wrong field, and logs a warning
for one that is unusually long. Whether a prompt fits the selected model's context window is a
question of tokens, for the model, and is not decided here.
"""

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

SMARTER_MAX_SYSTEM_ROLE_LENGTH = 32768
"""The maximum length of a system role, in characters, about 8,000 tokens.

A sanity bound, not a style rule.
"""

SMARTER_LONG_SYSTEM_ROLE_LENGTH = 8192
"""The length of a system role, in characters, above which a warning is logged, about 2,000 tokens."""


def warn_if_long_system_role(value: str, field: str) -> str:
    """
    Log a warning if a system role is longer than :data:`SMARTER_LONG_SYSTEM_ROLE_LENGTH`.

    It is sent with every prompt, so a long one costs tokens on every turn. It is allowed:
    the warning only makes it visible.

    :param value: The system role.
    :param field: The manifest field, for the warning, e.g. ``LLMClient.spec.config.defaultSystemRole``.
    :returns: The system role, unchanged.
    """
    if len(value) > SMARTER_LONG_SYSTEM_ROLE_LENGTH:
        logger.warning(
            "%s.warn_if_long_system_role() %s is %s characters long, more than %s. It is sent with every prompt.",
            logger_prefix,
            field,
            len(value),
            SMARTER_LONG_SYSTEM_ROLE_LENGTH,
        )
    return value


__all__ = ["SMARTER_LONG_SYSTEM_ROLE_LENGTH", "SMARTER_MAX_SYSTEM_ROLE_LENGTH", "warn_if_long_system_role"]
