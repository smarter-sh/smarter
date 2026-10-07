Authentication
================================

The Smarter platform uses an API key-based proprietary authentication strategy
based on Django Rest Framework's knox token authentication. API keys are used
for the command-line interface as well as for deployed LLMClients/Agents that
are configured to use authentication. See :doc:`../developer-reference/lib/drf/token-authentication/smarter-token-authentication` for details.
