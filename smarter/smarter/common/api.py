"""Smarter API enumerations."""

VERSION_PREFIX = "smarter.sh"


class SmarterApiVersions:
    """API Version enumeration."""

    V0 = f"{VERSION_PREFIX}/v0"
    V1 = f"{VERSION_PREFIX}/v1"

    @classmethod
    def all(cls):
        """Return the api versions: the class's upper-case string attributes, not its methods."""
        return [value for name, value in vars(SmarterApiVersions).items() if name.isupper() and isinstance(value, str)]
