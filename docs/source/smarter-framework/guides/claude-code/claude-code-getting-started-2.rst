Getting Started with Claude-Powered Coding in Smarter
=====================================================

Goal
----

Use a Claude-powered model in Smarter to assist with software development tasks
such as generating code, explaining logic, and refactoring functions.

Prerequisites
-------------

- A Smarter account
- Access to an environment where Smarter is deployed
- Basic understanding of REST APIs and JSON configuration
- Familiarity with development workflows

Setup
-----

Before starting, ensure the following:

- Smarter platform is accessible
- Anthropic API key is available
- Provider configuration capability is enabled in Smarter

Concept Overview
----------------

Smarter integrates Large Language Models (LLMs) through a provider-model abstraction.

Provider
~~~~~~~~

A provider represents an external LLM service (e.g., Anthropic).

Provider Model
~~~~~~~~~~~~~~

A provider model defines:

- the model identifier
- supported capabilities
- how Smarter interacts with the model

For Claude-based workflows, the provider must expose capabilities such as:

- text generation
- streaming responses
- tool usage (for advanced coding workflows)

Step-by-Step
------------

Step 1: Define Anthropic Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a provider entry representing Anthropic.

Key attributes:

- base_url: https://api.anthropic.com
- authentication: API key
- provider name: Anthropic

Step 2: Define Claude Model Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a model entry describing Claude capabilities.

The following example shows a minimal provider-model configuration:

.. literalinclude:: ../_examples/anthropic_provider_example.json
   :language: json
   :caption: Example Anthropic provider-model configuration
   :linenos:

Step 3: Load Configuration into Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Depending on your environment, configuration may be loaded through:

- database entries (admin UI)
- configuration files
- API-based provider registration

Once loaded, Smarter will register:

- the provider (Anthropic)
- the associated model (Claude)

Step 4: Verify Model Availability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter includes a provider verification mechanism.

Verification typically checks:

- text generation capability
- response formatting
- streaming support (if enabled)

Successful verification confirms the model is ready for use.

Step 5: Use Claude for Coding Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Navigate to Smarter’s interface and select the configured Claude model.

Example prompt:

"Write a Python function that validates an email address."

You can then extend the workflow:

- "Add unit tests"
- "Refactor for readability"
- "Explain the regex logic"

Proof of Concept
----------------

A successful setup allows developers to:

- generate working code
- receive explanations
- iterate on prompts interactively

Example outcome:

- Python function for email validation
- unit tests
- explanation of logic

This demonstrates a virtual coding pair workflow using Claude.

Troubleshooting
---------------

Provider Not Found
~~~~~~~~~~~~~~~~~

- Ensure provider configuration is loaded correctly
- Verify base_url and provider name

Authentication Errors
~~~~~~~~~~~~~~~~~~~~

- Confirm API key is valid
- Check environment variables or configuration source

Model Not Responding
~~~~~~~~~~~~~~~~~~~

- Ensure model capabilities match request type
- Verify endpoint compatibility with Smarter

Verification Failures
~~~~~~~~~~~~~~~~~~~~

- Check request/response format compatibility
- Ensure required capabilities are enabled

Best Practices
--------------

- Keep prompts specific and structured
- Use iterative refinement
- Validate generated code before production use

Conclusion
----------

By configuring Anthropic as a provider and defining a Claude-capable model,
Smarter enables developers to leverage AI-assisted coding workflows,
improving productivity and code quality.

.. toctree::
   :maxdepth: 1
   :caption: External Resources

   ../../external-links/claude-reference
   ../../external-links/support-smarter
   ../../external-links/swagger
   ../../external-links/manifest-reference
   ../../external-links/json-schemas
   ../../external-links/youtube
