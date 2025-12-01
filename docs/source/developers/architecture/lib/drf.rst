Django Rest Framework (DRF)
===========================

Smarter uses Django Rest Framework (DRF) for building its API endpoints. The following
components are the entirety of modifications and extensions made to DRF within the Smarter
codebase. These components primarily focus on adding and enhancing authentication mechanisms and
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
