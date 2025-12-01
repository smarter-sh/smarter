ExpiringTokenGenerator
======================

ExpiringTokenGenerator implements single-use authentication tokens that
expire after a configurable amount of time (24 hours by default). It is
designed to be used in scenarios such as password reset links or email
confirmation links, but could be used in other scenarios as well.

.. autoclass:: smarter.lib.django.token_generators.ExpiringTokenGenerator
    :members:
    :undoc-members:
    :show-inheritance:
    :exclude-members: __init__
