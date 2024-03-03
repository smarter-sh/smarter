# chatbot

Top class proprietary class for implementing a complete, standalone chatbot. Manages the following:

Manages the following:

- kind of chat engine: smarter chat, openai passthrough, langchain passthrough
- a subdomain of the form `domain-name.platform.smarter.sh` and/or a custom domain.
- an api: chat, billing history, etc.
- management features to enable/disable extensibility features: Wordpress plugin, etc.

Contains the following:

- a skinned/themed `chatapp`
- a list of `plugin` instances
- one of: `chat`, `passthrough_openai`, `passthrough_langchain`
- toggle features for other custom function-calling features: weather, etc.
