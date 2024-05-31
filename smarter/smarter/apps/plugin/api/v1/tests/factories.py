"""Plug helper functions for plugin unit tests."""

import requests


def create_generic_request():
    url = "http://example.com"
    headers = {"Content-Type": "application/json"}
    data = {}

    request = requests.Request("GET", url, headers=headers, data=data)
    prepared_request = request.prepare()

    return prepared_request
