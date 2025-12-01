Smarter Middleware
=======================

Smarter provides several custom middleware classes that extend Django's
middleware framework to add additional security features and specialized
support for ChatBot/Agent http requests.

.. autoclass:: smarter.lib.django.middleware.cors.SmarterCorsMiddleware
    :members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.django.middleware.csrf.SmarterCsrfViewMiddleware
    :members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.django.middleware.excessive_404.SmarterBlockExcessive404Middleware
    :members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.django.middleware.sensitive_files.SmarterBlockSensitiveFilesMiddleware
    :members:
    :show-inheritance:
    :exclude-members: __init__

.. autoclass:: smarter.lib.django.middleware.json.SmarterJsonErrorMiddleware
    :members:
    :show-inheritance:
    :exclude-members: __init__
