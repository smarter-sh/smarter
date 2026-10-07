# Built-in Proxies

Proxy manifests that `manage.py add_builtin_proxies` applies for the Smarter
admin, so that every account may use them. `manage.py initialize_platform`
calls it after `manage.py initialize_providers`, which creates the built-in
Providers and their API key Secrets, e.g. `openai` and `openai_api_key` from
the `OPENAI_API_KEY` environment variable.

A manifest is skipped if its Provider or Secret does not exist, e.g. because
the environment variable of its API key is not set.

Each one allows only its provider's inference endpoints, e.g. chat completions,
embeddings and models, so that the platform's provider accounts' files,
fine-tuning jobs, batches and settings cannot be reached through them.

| Proxy             | Provider     | API key Secret       | SDK            |
| ----------------- | ------------ | -------------------- | -------------- |
| `openai`          | `openai`     | `openai_api_key`     | OpenAI         |
| `anthropic`       | `anthropic`  | `anthropic_api_key`  | Anthropic      |
| `googleai`        | `googleai`   | `gemini_api_key`     | Google Gen AI  |
| `googleai_openai` | `googleai`   | `gemini_api_key`     | OpenAI         |
| `mistral`         | `mistral`    | `mistral_api_key`    | Mistral        |
| `cohere`          | `cohere`     | `cohere_api_key`     | Cohere         |
| `fireworks`       | `fireworks`  | `fireworks_api_key`  | OpenAI         |
| `togetherai`      | `togetherai` | `togetherai_api_key` | Together       |
| `metaai`          | `metaai`     | `llama_api_key`      | Llama API      |
