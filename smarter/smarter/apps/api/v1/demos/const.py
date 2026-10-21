"""Constants for the api's demo end points, ``/api/v1/demos/``."""

namespace = "demos"

STACKADEMY_API_CONNECTION_NAME = "smarter_test_api"
"""
The Stackademy ApiConnection, whose ``apiKey`` Secret is the password of the Stackademy course catalogue.

It is in the Stackademy project, https://github.com/smarter-sh/stackademy, which ``manage.py load_from_github``
applies. The course catalogue accepts the ``apiKey`` of the Smarter
account's connection, so the Secret's name is only in the connection's manifest.
"""
