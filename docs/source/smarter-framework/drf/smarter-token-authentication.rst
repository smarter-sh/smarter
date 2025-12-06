Smarter Token Authentication
=============================

Smarter extends Django Rest Framework's token authentication mechanism to implement
a more robust and feature-rich Api key based authentication system tailored to the needs of the Smarter platform.
The following components are designed to facilitate secure and efficient token-based authentication.
These components primarily focus on adding and enhancing authentication mechanisms and
providing specialized views for authenticated users.

The principal enhancements include:

- an ability to enable/disable token authentication via the Django admin console.
- a last-used timestamp on tokens to track their usage.

.. toctree::
    :maxdepth: 1

    token-authentication/smarter-token-authentication
    token-authentication/django-model
    token-authentication/smarter-token-authentication-middleware
    token-authentication/smarter-authenticated-list-api-view
    token-authentication/smarter-authenticated-api-view
