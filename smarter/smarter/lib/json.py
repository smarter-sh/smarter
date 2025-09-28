"""
JSON utilities.
"""

import json

# pylint: disable=unused-import
from json import JSONDecodeError, JSONDecoder, JSONEncoder

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


def loads(
    s,
    *,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    **kw,
):
    """
    JSON load with
    """

    return json.loads(
        s,
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kw,
    )
