"""Smarter API enumerations."""

VERSION_PREFIX = "smarter.sh"


class SmarterApiVersions:
    """API Version enumeration."""

    V0 = f"{VERSION_PREFIX}/v0"
    V1 = f"{VERSION_PREFIX}/v1"

    @classmethod
    def all_values(cls):
        return [value for name, value in vars(SmarterApiVersions).items() if not name.startswith("__")]
