"""
Utility functions for settings.
"""

from pydantic import field_validator


def before_field_validator(*args, **kwargs):
    """
    Wrapper for pydantic field_validator with mode='before'.
    """
    kwargs["mode"] = "before"
    return field_validator(*args, **kwargs)
