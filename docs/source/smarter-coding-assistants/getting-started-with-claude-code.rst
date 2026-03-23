Getting Started with Claude Code on Smarter
===========================================

Overview
--------

This tutorial walks you through integrating Anthropic's Claude Code model into the Smarter platform and using it as a coding assistant for a simple development task. By the end, you will have a working Claude Code provider configured in Smarter and will use it to generate and refine code.

---

a. Goal
-------

We will use Claude Code with Smarter to generate, review, and refine a simple Python utility that parses log files and extracts error summaries.

---

b. Prerequisites
----------------

You are expected to have:

- Strong familiarity with REST APIs and JSON
- Working knowledge of Python (or your primary development language)
- Experience with environment variables and secure credential handling
- Basic understanding of LLM concepts (tokens, prompts, completions)
- Access to:
  - A valid Smarter account
  - An Anthropic API key with access to Claude models

---

c. Setup
--------

1. Obtain Anthropic API Credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Navigate to the Anthropic console
- Generate an API key
- Store it securely (e.g., environment variable):

.. code-block:: bash

   export ANTHROPIC_API_KEY="your_api_key_here"

2. Review Smarter Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter requires defining a provider with:

- Provider name
- API base URL
- Authentication method
- Model definitions
- Request/response mappings

Reference:
https://docs.smarter.sh/en/latest/smarter-resources/smarter-provider.html

3. Create a New Provider Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new provider configuration file:

.. code-block:: yaml

   provider:
     name: anthropic
     display_name: Anthropic Claude
     base_url: https://api.anthropic.com/v1
     auth:
       type: api_key
       header: x-api-key
       value: ${ANTHROPIC_API_KEY}

   models:
     - name: claude-code
       display_name: Claude Code
       endpoint: /messages
       method: POST
       request:
         headers:
           anthropic-version: "2023-06-01"
           content-type: application/json
         body_template:
           model: "claude-3-opus-20240229"
           max_tokens: {{max_tokens}}
           messages:
             - role: user
               content: "{{prompt}}"
       response:
         output_path: content[0].text

4. Register Provider in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Place the YAML file in the Smarter providers directory
- Restart or reload Smarter services (depending on deployment)
- Verify provider appears in UI under available models

---

d. Concept Overview
------------------

Smarter Provider Abstraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter decouples model providers from user workflows via a provider abstraction layer. Each provider defines:

- API endpoint structure
- Authentication scheme
- Prompt/response mapping

Claude Code Model
~~~~~~~~~~~~~~~~~

Claude Code is optimized for:

- Code generation
- Refactoring
- Debugging
- Explanation of complex logic

It operates via structured message input rather than raw prompt strings.

Prompt Engineering for Code
~~~~~~~~~~~~~~~~~~~~~~~~~~

Effective prompts typically include:

- Explicit task definition
- Constraints (language, performance, style)
- Input/output examples
- Context (existing code)

---

e. Step-by-Step
---------------

Step 1: Validate Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From Smarter UI:

- Navigate to "Models"
- Select "Anthropic Claude"
- Choose "Claude Code"
- Run a test prompt:

.. code-block:: text

   Write a Python function that adds two numbers.

Expected output: valid Python function.

---

Step 2: Create a Coding Prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We will define a log parser requirement:

.. code-block:: text

   Write a Python script that:
   - Reads a log file
   - Extracts lines containing "ERROR"
   - Outputs a summary count by error type

---

Step 3: Execute Prompt in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Open Smarter prompt interface
- Select Claude Code model
- Paste prompt
- Execute

---

Step 4: Refine Output
~~~~~~~~~~~~~~~~~~~~~

Iterate with follow-up prompts:

.. code-block:: text

   Optimize this code for large files using streaming instead of loading into memory.

.. code-block:: text

   Add unit tests using pytest.

---

Step 5: Integrate into Local Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Copy generated code into your IDE
- Validate execution
- Commit to version control

---

f. Proof of Concept
------------------

Expected Output Example:

.. code-block:: python

   def summarize_errors(log_file):
       error_counts = {}
       with open(log_file, 'r') as f:
           for line in f:
               if "ERROR" in line:
                   error_type = line.split("ERROR")[1].strip()
                   error_counts[error_type] = error_counts.get(error_type, 0) + 1
       return error_counts

   if __name__ == "__main__":
       summary = summarize_errors("app.log")
       print(summary)

You should be able to:

- Run the script successfully
- See aggregated error counts
- Iterate on improvements using Claude Code

---

g. Troubleshooting
-----------------

Provider Not Found in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Verify YAML syntax
- Confirm file placement in providers directory
- Restart Smarter services

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~

- Ensure API key is valid
- Confirm header mapping: ``x-api-key``
- Check environment variable resolution

Malformed Responses
~~~~~~~~~~~~~~~~~~~

- Validate ``response.output_path``
- Inspect raw API response via logs
- Adjust parsing path if Anthropic response format changes

Model Not Responding
~~~~~~~~~~~~~~~~~~~

- Confirm correct model identifier
- Check API quota / rate limits
- Review network connectivity

Poor Code Quality
~~~~~~~~~~~~~~~~~

- Improve prompt specificity
- Add constraints and examples
- Use iterative refinement rather than single-shot prompts

---

Conclusion
----------

You now have:

- A working Anthropic provider in Smarter
- Access to Claude Code for development tasks
- A repeatable workflow for integrating LLM-assisted coding into your daily work

Next Steps:

- Integrate with IDE plugins (handled by platform team)
- Standardize prompt templates across teams
- Track token usage via accounting integration
