"""
Overridden JSON utilities. The effective modifications are
- Use DjangoJSONEncoder as the default encoder
- Standardize indentation to 2 characters
- Use str as the default for non-serializable objects
"""

import json

# pylint: disable=unused-import
from json import (  # unmodified re-export
    JSONDecodeError,
    JSONDecoder,
    JSONEncoder,
    load,
    loads,
)

from django.core.serializers.json import DjangoJSONEncoder


def dumps(
    obj,
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    """
    JSON dump with
    - DjangoJSONEncoder as default encoder
    - indent of 2
    - default of str
    """

    return json.dumps(
        obj,
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        cls=cls or DjangoJSONEncoder,
        indent=indent or 2,
        separators=separators,
        default=default or str,
        sort_keys=sort_keys,
        **kw,
    )
