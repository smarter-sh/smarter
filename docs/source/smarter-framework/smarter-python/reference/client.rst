..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

The Client
==========

``smarter.client``
------------------

.. py:module:: smarter.client

The Smarter client.

.. code-block:: python

    from smarter import Smarter

    client = Smarter()                      # SMARTER_API_KEY, or ~/.smarter/config.yaml
    print(client.whoami().user.username)

    response = client.llm_clients.prompt(5, "What is 17 times 23?")
    print(response.text)

.. py:class:: Smarter(*, api_key: Optional[str] = None, base_url: Optional[str] = None, environment: Optional[Literal['local', 'alpha', 'beta', 'next', 'prod']] = None, timeout: Optional[float] = None, max_retries: Optional[int] = None, default_headers: Optional[collections.abc.Mapping[str, str]] = None, http_client: Optional[httpx.Client] = None) -> None

   A client of a Smarter platform's api.

   Every argument is optional. See :mod:`smarter.core.conf` for where each is looked up.

   :param api_key: A Smarter api key.
   :param base_url: The platform's url, e.g. ``https://platform.example.com`` or ``http://localhost:9357``.
   :param environment: The environment of the smarter cli's configuration file to use: ``local``,
       ``alpha``, ``beta``, ``next`` or ``prod``.
   :param timeout: The request timeout, in seconds.
   :param max_retries: How many times to retry a request that failed for a transient reason, e.g.
       a timeout, a 429 or a 502. 0 disables retries.
   :param default_headers: Headers to add to every request.
   :param http_client: An ``httpx.Client`` to send the requests, e.g. one with a proxy. The client
       does not close a client that it was given.
   :raises SmarterConfigurationError: If no api key is found.

   The client's attributes group the api's operations:

   - :attr:`manifests`: apply, validate, get, describe, delete, deploy, undeploy and logs, for any kind
   - :attr:`llm_clients`: LLMClients, and prompting and chatting with them
   - :attr:`guardrails`, :attr:`mcp_clients`, :attr:`vectorstores`, :attr:`llm_hosts`,
     :attr:`secrets`, :attr:`plugins`, :attr:`orchestrators`, :attr:`vectorsearches`
   - :attr:`accounts` (and ``accounts.users`` and ``accounts.contacts``)
   - :attr:`history`, :attr:`journal`, :attr:`providers`, :attr:`proxies`
   - :meth:`whoami`, :meth:`version`, :meth:`status` and :meth:`kinds`

   Use it as a context manager, or call :meth:`close`, to close its connections.

   .. py:property:: api_key

      The api key, e.g. to use a proxy with a provider's own SDK.


   .. py:property:: base_url

      The api's base url, e.g. ``https://platform.smarter.sh/api/v1/``.


   .. py:property:: manifests

      The manifest api, for any resource kind.


   .. py:property:: llm_clients

      LLMClients.


   .. py:property:: guardrails

      Guardrails.


   .. py:property:: mcp_clients

      MCPClients.


   .. py:property:: vectorstores

      Vectorstores.


   .. py:property:: llm_hosts

      LLMHosts.


   .. py:property:: secrets

      Secrets.


   .. py:property:: plugins

      Plugins.


   .. py:property:: orchestrators

      Orchestrators.


   .. py:property:: vectorsearches

      Vectorsearches.


   .. py:property:: accounts

      Accounts, and their users and contacts.


   .. py:property:: history

      The history of chat sessions, tool calls and plugin uses.


   .. py:property:: journal

      The Smarter Journal.

      Superusers only.


   .. py:property:: providers

      LLM providers and their models.


   .. py:property:: proxies

      Proxies to LLM providers' own apis.


   .. py:method:: whoami() -> smarter.models.platform.WhoAmI

      The owner of the api key: the user, their account, and the platform's environment.

      :returns: The owner.


   .. py:method:: version() -> smarter.models.platform.PlatformVersion

      The platform's version, and the versions of its main Python packages.

      :returns: The versions.


   .. py:method:: status() -> smarter.models.platform.PlatformStatus

      The state of the platform's infrastructure and compute.

      :returns: The status.


   .. py:method:: kinds() -> list[smarter.models.manifest.KindInfo]

      The resource kinds that the platform supports, and which of them can be deployed.

      :returns: The kinds.


   .. py:method:: close() -> None

      Close the client's connections.
