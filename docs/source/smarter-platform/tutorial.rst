Tutorial
========

Getting Started: Building a Modern Todo List Web App with Smarter and Claude Code

Goal
----
We will use Anthropic Claude (via a custom LLM provider in Smarter) to create a complete single-file HTML web application for a modern Todo List with the following features:

- Add, edit, delete, and complete tasks
- Persistence with local storage
- Responsive design using Tailwind CSS
- Clean and modern UI

By the end of this tutorial, you will have a fully functional Todo app generated entirely by your Smarter-powered coding assistant.

Prerequisites
-------------
This tutorial assumes you already have:

- Basic familiarity with YAML syntax and command-line tools.
- An Anthropic API key for access to Claude models.
- Smarter platform installed and running locally in your environment.
- Access to the Smarter Web Dashboard -> Prompt Engineer Workbench.
- A modern web browser to test the generated HTML file.
- Basic understanding of HTML, CSS, and JavaScript.

Setup
-----
Before you begin, complete these preparation steps:

1. Ensure the smarter CLI is installed and authenticated.
2. Have your Anthropic API key ready.
3. Start your Smarter instance.

Concept Overview
----------------
Smarter is a declarative, no-code platform for managing AI resources. Key concepts used in this tutorial:

- **Provider**: Defines an LLM provider to be used by the Chatbot to access Anthropic Claude models.
- **Chatbot**: The main conversational agent containing the system prompt, model settings, and temperature. This is what you interact with in the Workbench and what IDE extensions would call.
- **Prompt Engineer Workbench**: The web interface inside Smarter where you can chat with your Chatbot to generate code, iterate, and prototype rapidly.
- **Single-file HTML**: A self-contained web app (HTML + Tailwind CSS + embedded JS) that requires no build step or server.

Step-by-Step
------------

**Step 1: Create a Secret for the API Key**

Create a file named ``claude-secret.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Secret
   metadata:
     name: claude-api-key
     description: Anthropic API key for Claude
   spec:
     data:
       api_key: "xxxxx"   # Replace with your Anthropic key

Apply it:

.. code-block:: bash

   smarter apply -f claude-secret.yaml

**Step 2: Add Claude as a New LLM Provider**

Create ``claude-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: claude
     description: Claude Code
     version: "1.0.0"
     tags: ["llm", "coding", "claude"]
   spec:
     provider:
       name: "Claude"
       description: "Anthropic Claude models for coding assistance"
       base_url: "https://api.anthropic.com/v1"
       api_key: "claude-api-key"
       connectivity_test_path: "/models"

Apply the provider:

.. code-block:: bash

   smarter apply -f claude-provider.yaml

Verify it works:

.. code-block:: bash

   smarter describe provider claude

**Step 3: Create the Coding Assistant Chatbot**

Create ``web-coding-assistant.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     name: web-coding-assistant
     description: Coding assistant for generating modern web apps
     version: "1.0.0"
     tags: ["coding", "web"]
   spec:
     config:
       provider: "Claude"
       defaultModel: "claude-3-5-sonnet-20241022"
       defaultSystemRole: |
         You are an expert full-stack web developer specializing in clean, modern single-file HTML applications.
         Always use Tailwind CSS. Output ONLY the complete, valid HTML file when asked.
         Never add explanations outside the HTML.
       temperature: 0.1
       maxTokens: 16384
     plugins: []

Apply the chatbot:

.. code-block:: bash

   smarter apply -f web-coding-assistant.yaml

**Step 4: Generate the Todo App in the Prompt Engineer Workbench**

1. Open Smarter Web Dashboard -> Prompt Engineer Workbench.
2. Select the chatbot **web-coding-assistant**.
3. Paste the following prompt:

::

    Create a complete single-file HTML web application for a modern Todo List with these features:

    Add, edit, delete, and mark tasks as complete
    Tasks saved automatically in local storage
    Use Tailwind CSS

    Output ONLY the complete, valid HTML file content.
    Do not include any markdown, explanations, or extra text outside the HTML.

4. Send the message and the assistant will return the full HTML.
5. Copy everything from ``<!DOCTYPE html>`` to the end and save it as ``todo-app.html``.
6. Open the file in your browser and test all features.

Proof of Concept
----------------
When successful, you will have a single file ``todo-app.html`` that:

- Runs entirely in the browser with no backend or build tools.
- Looks professional with modern styling.
- Persists your tasks across page refreshes.

Troubleshooting
---------------
Solutions to common pitfalls:

- Provider fails connectivity test

  - Verify the API key in the secret and ``base_url`` is correct. Re-apply the Provider manifest for any corrections.

- Generated HTML is truncated

  - Increase ``maxTokens`` in the Chatbot config and re-apply, or use a more powerful model like Claude 3.5 Sonnet.

- Output contains explanations instead of pure HTML

  - Adjust the system prompt wording to reinforce "ONLY output the complete HTML file” and re-generate.

Next Steps
----------
- Build a VS Code extension that calls your Chatbot API for inline assistance.
- Experiment with additional prompts to add features to the Todo App in the Workbench.

You have now successfully used Smarter as a self-hosted coding assistant to generate a complete web application.