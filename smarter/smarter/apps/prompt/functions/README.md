# Smarter Functions

These are built-in LLM tool-call functions that can be optionally
added to any ChatBot by adding the function name to the manifest
label, 'functions'

## Registering a function

Contributors: add your new function to the following

- smarter.apps.chatbot.models.ChatBotFunctions.CHOICES
- smarter.apps.prompt.providers.base_classes.ChatProviderBase.tools
- smarter.apps.prompt.providers.base_classes.ChatProviderBase.available_functions
- smarter.apps.prompt.providers.base_classes.OpenAICompatibleChatProvider.process_tool_call()
- smarter.apps.prompt.providers.base_classes.OpenAICompatibleChatProvider.handle_function_provided()
