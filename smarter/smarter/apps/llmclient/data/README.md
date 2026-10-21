# Example LLMClients

- `llm-clients/`: the example LLMClients, e.g. `smarter`. `manage.py add_example_llmclients`
  applies them, and `manage.py deploy_example_llmclients` deploys them.
- The Stackademy LLMClients are in their own repository, https://github.com/smarter-sh/stackademy,
  with the rest of the Stackademy project. `manage.py load_from_github` applies it, and
  `manage.py verify_stackademy` prompts its LLMClients to verify that they work.
- `custom-domains/`: the example CustomDomains, which `manage.py add_example_custom_domains`
  applies.
