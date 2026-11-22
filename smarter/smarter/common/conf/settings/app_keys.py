# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""
The api keys of Smarter's apps: the built-in Providers', the search plugins', the managed vector databases'.

Each is a ``SecretStr``, so that it is masked wherever it is shown, e.g. in the app's log line at
startup. Each app's ``manage.py initialize_*`` command stores its keys as Smarter Secrets.
"""

from typing import Optional

from pydantic import BaseModel, Field, SecretStr

from smarter.common.conf.defaults import settings_defaults


class AppKeySettings(BaseModel):
    """The api keys of Smarter's apps, by their ``SMARTER_APP_<APP>_*`` environment variables."""

    app_provider_anthropic_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_ANTHROPIC_API_KEY,
        description="Anthropic's api key, for the built-in anthropic Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_ANTHROPIC_API_KEY",
    )
    """Anthropic's api key, for the built-in anthropic Provider: ``SMARTER_APP_PROVIDER_ANTHROPIC_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_cohere_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_COHERE_API_KEY,
        description="Cohere's api key, for the built-in cohere Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_COHERE_API_KEY",
    )
    """Cohere's api key, for the built-in cohere Provider: ``SMARTER_APP_PROVIDER_COHERE_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_fireworks_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_FIREWORKS_API_KEY,
        description="Fireworks AI's api key, for the built-in fireworks Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_FIREWORKS_API_KEY",
    )
    """Fireworks AI's api key, for the built-in fireworks Provider: ``SMARTER_APP_PROVIDER_FIREWORKS_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_gemini_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_GEMINI_API_KEY,
        description="Google AI's api key, for the built-in googleai Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_GEMINI_API_KEY",
    )
    """Google AI's api key, for the built-in googleai Provider: ``SMARTER_APP_PROVIDER_GEMINI_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_google_maps_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_GOOGLE_MAPS_API_KEY,
        description="Google Maps' api key, for the weather extension. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_GOOGLE_MAPS_API_KEY",
    )
    """Google Maps' api key, for the weather extension: ``SMARTER_APP_PROVIDER_GOOGLE_MAPS_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_google_service_account_b64: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64,
        description="Google service account credentials, base64-encoded, for Google Cloud bearer tokens. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64",
    )
    """Google service account credentials, base64-encoded, for Google Cloud bearer tokens: ``SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64``.

    None if it is not set, or a placeholder.
    """

    app_provider_llama_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_LLAMA_API_KEY,
        description="Meta's Llama api key, for the built-in metaai Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_LLAMA_API_KEY",
    )
    """Meta's Llama api key, for the built-in metaai Provider: ``SMARTER_APP_PROVIDER_LLAMA_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_mistral_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_MISTRAL_API_KEY,
        description="Mistral's api key, for the built-in mistral Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_MISTRAL_API_KEY",
    )
    """Mistral's api key, for the built-in mistral Provider: ``SMARTER_APP_PROVIDER_MISTRAL_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_openai_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_OPENAI_API_KEY,
        description="OpenAI's api key, for the built-in openai Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_OPENAI_API_KEY",
    )
    """OpenAI's api key, for the built-in openai Provider: ``SMARTER_APP_PROVIDER_OPENAI_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_provider_togetherai_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_PROVIDER_TOGETHERAI_API_KEY,
        description="Together AI's api key, for the built-in togetherai Provider. Masked by pydantic SecretStr.",
        title="APP_PROVIDER_TOGETHERAI_API_KEY",
    )
    """Together AI's api key, for the built-in togetherai Provider: ``SMARTER_APP_PROVIDER_TOGETHERAI_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_llmtool_brave_search_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_LLMTOOL_BRAVE_SEARCH_API_KEY,
        description="Brave Search's api key, for ImageSearchPlugins and the Brave web search samples. Masked by pydantic SecretStr.",
        title="APP_LLMTOOL_BRAVE_SEARCH_API_KEY",
    )
    """Brave Search's api key, for ImageSearchPlugins and the Brave web search samples: ``SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_llmtool_tavily_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_LLMTOOL_TAVILY_API_KEY,
        description="Tavily's api key, for WebsearchPlugins. Masked by pydantic SecretStr.",
        title="APP_LLMTOOL_TAVILY_API_KEY",
    )
    """Tavily's api key, for WebsearchPlugins: ``SMARTER_APP_LLMTOOL_TAVILY_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_vectorstore_pinecone_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_VECTORSTORE_PINECONE_API_KEY,
        description="Pinecone's api key, for the managed Pinecone vector database. Masked by pydantic SecretStr.",
        title="APP_VECTORSTORE_PINECONE_API_KEY",
    )
    """Pinecone's api key, for the managed Pinecone vector database: ``SMARTER_APP_VECTORSTORE_PINECONE_API_KEY``.

    None if it is not set, or a placeholder.
    """

    app_vectorstore_qdrant_cloud_api_key: Optional[SecretStr] = Field(
        settings_defaults.APP_VECTORSTORE_QDRANT_CLOUD_API_KEY,
        description="Qdrant Cloud's api key, for the managed Qdrant Cloud vector database. Masked by pydantic SecretStr.",
        title="APP_VECTORSTORE_QDRANT_CLOUD_API_KEY",
    )
    """Qdrant Cloud's api key, for the managed Qdrant Cloud vector database: ``SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_API_KEY``.

    None if it is not set, or a placeholder.
    """
