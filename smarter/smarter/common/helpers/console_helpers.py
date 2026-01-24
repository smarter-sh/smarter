"""Console helpers for formatting output."""

import os
from typing import Union

from dotenv import load_dotenv

from smarter.common.const import SmarterEnvironments
from smarter.lib import json

load_dotenv()

environment = os.environ.get("ENVIRONMENT", SmarterEnvironments.LOCAL)


def formatted_json(json_obj: Union[dict, list]) -> str:

    pretty_json = json.dumps(json_obj)
    if environment != SmarterEnvironments.LOCAL:
        return pretty_json
    return f"\033[32m{pretty_json}\033[0m"


def formatted_text(text: str) -> str:

    # bright green
    # return f"\033[92m{text}\033[0m"

    # regular green
    # return f"\033[32m{text}\033[0m"

    # bright red
    # return f"\033[91m{text}\033[0m"

    if environment != SmarterEnvironments.LOCAL:
        return text
    # bold and dark red
    return f"\033[1;31m{text}\033[0m"


def formatted_text_green(text: str) -> str:

    if environment != SmarterEnvironments.LOCAL:
        return text
    # bright green
    return f"\033[92m{text}\033[0m"


def formatted_text_red(text: str) -> str:

    if environment != SmarterEnvironments.LOCAL:
        return text
    # bright red
    return f"\033[91m{text}\033[0m"
