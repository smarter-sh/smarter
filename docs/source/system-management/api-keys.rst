API Keys
========

Smarter API keys are used to authenticate and authorize access to Smarter AI resources like deployed ChatBot/Agent resources.
They are independently managed from the AI resources themselves, allowing for better security and flexibility.

Smarter API key are created on the Django knox TokenAuthentication system, a popular and well-supported authentication system for Django REST Framework.
See `smarter/lib/drf/token_authentication.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/drf/token_authentication.py>`_
for more details. Smarter adds a toggle to enable/disable API keys without deleting them, allowing for temporary suspension of access if needed.

Creating API Keys
-----------------

.. code-block:: bash

   python manage.py create_api_key \
    --account_number ####-####-#### \
    --username USERNAME \
    --description "This key is used for accessing the ChatBot API."

This will output the generated API key to the console. Be sure to store this key securely as it will not be shown again.

Managing API Keys
-----------------

Use Django admin to view, enable/disable, or delete existing API keys.

Configuration Options
---------------------

Smarter inherits and extends `Django Knox AuthToken <https://jazzband.github.io/django-rest-knox/>`__, which itself has several configuration options
that can be set in the Django settings file.

`SMARTER_API_KEY_MAX_LIFETIME_DAYS <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/const.py#L41>`__ determines the maximum recommended lifetime of
an API key in days. After this period, the application will generate warnings in the logs indicating that the key is beyond its
recommended expiration.

.. code-block:: python

    # Maximum lifetime of an API key in days. After this period, the key will expire and become invalid.
    SMARTER_API_KEY_MAX_LIFETIME_DAYS = 365 * 3  # 3 years

Extensions to the Django Know model include the following fields and methods:

.. code-block:: python

    class SmarterAuthToken(AuthToken, TimestampedModel):

        description = models.CharField(max_length=255, blank=True, null=True)
        last_used_at = models.DateTimeField(blank=True, null=True)
        is_active = models.BooleanField(default=True)
        def activate(self):
        def deactivate(self):
        def toggle_active(self):


Using API Keys
-----------------

To use an API key, associate it with ChatBot/Agent resources when creating them via the Smarter REST API. The Smarter API will validate the API key on each request,
which includes business rule enforcement like rate limiting, access control, and basic declarative referential integrity such as ensuring the API key belongs
to the same Account as the resource being accessed.


Smarter Chat React Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Backend: see `smarter/lib/drf/views/token_authentication_helpers.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/drf/views/token_authentication_helpers.py>`_

.. code-block:: python

  @method_decorator(login_required, name="dispatch")
  class SmarterAuthenticatedAPIView(APIView, SmarterRequestMixin):
      """
      Allows access only to authenticated users.
      """

      authentication_classes = [SmarterTokenAuthentication]


Client front-end: see `https://github.com/smarter-sh/smarter-chat <https://github.com/smarter-sh/smarter-chat>`_

.. code-block:: json

  {
      "method": "POST",
      "credentials": "include",
      "mode": "cors",
      "headers": {
          "Authorization": "Token YOUR_API_KEY_HERE",
          "Accept": "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": "q9WXqqIhYJMI3ZSBIOE18JMORBMqAHri",
          "Origin": "http://localhost:8000",
          "Cookie": "session_key=a07593ecfaecd24008ca4251096732663ac0213b8cc6bdcce4f4c043276ab0b5; debug=true;"
      },
      "body": "the request body goes here..."
  }

Smarter Command-line Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

API Backend: see `smarter/apps/api/v1/cli/views/base.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/views/base.py>`_

.. code-block:: python

  class CliBaseApiView(APIView, SmarterRequestMixin):
    """
    Base API view for CLI commands.
    """
    authentication_classes = (SmarterTokenAuthentication,)

Client front-end: see `https://github.com/smarter-sh/smarter-cli <https://github.com/smarter-sh/smarter-cli>`_

.. code-block:: bash

   smarter whoami --api_key YOUR_API_KEY_HERE
