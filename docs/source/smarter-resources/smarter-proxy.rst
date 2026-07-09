Smarter Proxy
=====================

Overview
--------

Smarter Proxy is a built-in service that provides seamless access to third-party
LLM API backends. Smarter Resources route their LLM calls through the proxy
rather than connecting to a provider directly; the proxy forwards each request
to the appropriate backend and returns the response, presenting a consistent
interface regardless of which provider sits underneath.

Because every call passes through Smarter Proxy, it is also the natural point
at which the platform's low-level services get applied: requests and responses
are logged, budget constraints are enforced before a call is allowed to proceed,
and activity is recorded to the Smarter Journal.

Smarter Proxy also shields third-party LLM API credentials from the calling
application. Credentials are held and injected by the proxy itself, so client
code, end users, and downstream Smarter Resources never see or handle the
underlying provider keys directly.
