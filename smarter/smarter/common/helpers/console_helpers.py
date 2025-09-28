"""Console helpers for formatting output."""

from typing import Union

from smarter.lib import json


def formatted_json(json_obj: Union[dict, list]) -> str:
    pretty_json = json.dumps(json_obj)
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


def formatted_text_green(text: str) -> str:

    # bright green
    return f"\033[92m{text}\033[0m"


def formatted_text_red(text: str) -> str:

    # bright green
    return f"\033[31m{text}\033[0m"
