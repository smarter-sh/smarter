# Smarter Functions

These are built-in LLM tool-call functions that can be optionally
added to any LLMClient by adding the function name to the manifest
label, 'functions'

## Registering a function

Contributors: add your new function to the following

- smarter.apps.llm_client.models.LLMClientFunctions.CHOICES
- smarter.apps.prompt.functions

See also:

- smarter.apps.provider.services.text_completion.lib.OpenAICompatibleChatProvider.process_tool_call()
- smarter.apps.provider.services.text_completion.lib.OpenAICompatibleChatProvider.handle_function_provided()
