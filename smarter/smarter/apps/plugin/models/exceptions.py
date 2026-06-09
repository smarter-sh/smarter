"""
Exceptions for the Plugin app.
"""

# python stuff
from smarter.common.exceptions import SmarterValueError


class PluginDataValueError(SmarterValueError):
    """Custom exception for PluginData SQL errors."""
