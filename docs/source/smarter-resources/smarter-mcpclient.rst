Smarter MCP Client
=====================

Overview
--------

The Smarter MCP Client app provides a standardized interface for connecting large
language models to external tools and services through the Model Context Protocol (MCP).
Rather than implementing provider-specific integrations for each application,
the MCP Client discovers available tools from one or more MCP servers, negotiates
their capabilities, and exposes them to the Smarter orchestration engine as managed
resources. This allows prompts and engineering loops to invoke databases, APIs,
file systems, development tools, enterprise applications, or custom services
through a consistent protocol, while Smarter remains responsible for authentication,
authorization, auditing, and execution management. By separating tool implementation
from application logic, the MCP Client enables new capabilities to be added or
updated without modifying the surrounding AI application.

The MCP Client operates as a managed integration layer between Smarter and the
external MCP ecosystem. During initialization it establishes secure sessions
with configured MCP servers, retrieves their advertised tool definitions, and
makes those tools available for controlled invocation by prompts, agents, and
workflows. Each tool invocation is executed through Smarter’s existing security,
logging, charging, and mcpclient infrastructure, ensuring that external
capabilities remain subject to the same governance and operational controls
as native Smarter resources. This architecture allows organizations to adopt
the rapidly growing ecosystem of MCP-compatible services while maintaining
centralized configuration, observability, and policy enforcement across all
AI-assisted interactions.

The Smarter MCP Client app is included in v0.15.0 and later. It enables Account
administrators to configure and manage connections to MCP servers through the
Smarter administration interface, eliminating the need to hard-code tool
integrations or distribute MCP connection details across individual applications.

.. seealso::

    - :doc:`Smarter Installation Guide <../smarter-platform/installation>`
    - :doc:`OpenAI Getting Started Guide <../smarter-framework/guides/openai-api-getting-started-guide>`

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   mcpclient/api
   mcpclient/const
   mcpclient/management
   mcpclient/manifest
   mcpclient/models
   mcpclient/serializers
   mcpclient/signals
   mcpclient/tasks
   mcpclient/views
