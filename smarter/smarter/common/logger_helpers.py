# -*- coding: utf-8 -*-
"""Logger helpers."""

import datetime
import json


def formatted_json(json_obj: json) -> str:
    def handle_datetime(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    pretty_json = json.dumps(json_obj, indent=4, default=handle_datetime)
    return f"\033[32m{pretty_json}\033[0m"


def formatted_text(text: str) -> str:
    # bright green
    # return f"\033[92m{text}\033[0m"

    # regular green
    # return f"\033[32m{text}\033[0m"

    # dark red
    # return f"\033[31m{text}\033[0m"

    # bold and dark red
    return f"\033[1;31m{text}\033[0m"
