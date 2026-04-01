Getting Started with Claude Code in Smarter
===========================================

Goal
----
We will use Claude Code with Smarter to extend our platform’s LLM capabilities. By the end of this tutorial, you will have successfully configured an LLM provider within Smarter and verified it with a basic prompt.

Prerequisites
-------------
Before you begin, you should already have:

- A working Smarter account (credentials provided).
- Basic knowledge of LLM APIs and provider integrations.
- Familiarity with Python 3.11+ and virtual environments.
- Understanding of REST APIs, JSON, and authentication headers.
- Comfort with editing YAML configuration files.

Setup
-----
1. **Clone the Repository**  
   Ensure you have the Smarter repository locally:
git clone https://github.com/your-org/smarter.git

cd smarter
2. **Create a Virtual Environment**  
python -m venv venv
source venv/bin/activate # Linux/macOS
venv\Scripts\activate # Windows
3. **Install Dependencies**  
pip install -r requirements.txt
4. **Verify Smarter CLI**  
Confirm the `smarter` CLI is accessible:
smarter --version


Concept Overview
----------------
Integrating an LLM provider into Smarter involves three main concepts:

- **Provider Configuration:** Smarter stores all provider credentials and metadata in `providers.yaml`. Each LLM requires an API key and endpoint specification.
- **Prompt Execution:** When a request is made, Smarter routes prompts to the configured provider and returns the response.
- **Safety and Rate Limits:** Smarter enforces concurrency limits per provider. Proper configuration ensures your LLM usage is efficient and safe.

Step-by-Step Guide
-----------------

1. **Add the Claude Code Provider**

Edit `config/providers.yaml` and add the following entry:
```yaml
claude_code:
  api_key: YOUR_CLAUDE_API_KEY
  endpoint: https://api.claude.ai/code
  timeout: 30  # seconds
  max_tokens: 2048

2. Verify Connectivity

Use the Smarter CLI to test:
smarter test-provider claude_code

3. Expected output:
Provider claude_code reachable: True

Create a Sample Prompt

Save the following as test_prompt.json:
{
    "provider": "claude_code",
    "prompt": "Generate a Python function that returns the Fibonacci sequence up to n."
}

4. Send Prompt via Smarter

smarter run test_prompt.json

5. Inspect the Response

Smarter will return a JSON payload containing:

{
    "output": "def fibonacci(n): ...",
    "tokens_used": 42
}

Proof of Concept

If completed successfully, your Smarter setup with Claude Code should:

Accept a prompt and return a valid response.
Include metadata such as tokens used and runtime duration.
Confirm provider connectivity in CLI tests.
Troubleshooting
Error: Invalid API Key
Ensure the key in providers.yaml matches the one from Claude Code’s dashboard.
Timeout Issues
Increase timeout in providers.yaml if your prompts take longer than expected.
Unexpected Response Format
Check max_tokens and temperature settings for consistency with your prompt.
CLI Cannot Find Provider
Verify the YAML indentation and that smarter was restarted after editing configuration files.
Network Errors
Ensure your firewall or proxy allows outbound requests to https://api.claude.ai.

.. note::
NEVER run smarter run with production prompts unless you have verified connectivity and configuration locally. Misconfigured providers may result in API billing issues or invalid outputs.
