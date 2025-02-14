"""
This module contains helper functions for LLM prompting.
"""

import datetime


def get_date_time_string() -> str:
    """
    Get the current date and time in a human-readable format.
    """
    return f"The current date/time is {datetime.datetime.now().astimezone().strftime('%A, %Y-%m-%dT%H:%M:%S%z')}\n"
