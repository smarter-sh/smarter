Smarter Token Authentication
=============================

Smarter extends Django Rest Framework's token authentication mechanism to implement
a more robust and feature-rich Api key based authentication system tailored to the needs of the Smarter platform.
The following components are designed to facilitate secure and efficient token-based authentication.
These components primarily focus on adding and enhancing authentication mechanisms and
providing specialized views for authenticated users.

.. autoclass:: smarter.lib.drf.token_authentication.SmarterTokenAuthentication
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.drf.middleware.SmarterTokenAuthenticationMiddleware
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.drf.views.token_authentication_helpers.SmarterAuthenticatedAPIView
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__


.. autoclass:: smarter.lib.drf.views.token_authentication_helpers.SmarterAuthenticatedListAPIView
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
