..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAMLLMClient
============

``smarter.models.sam.llmclient``
--------------------------------

.. py:module:: smarter.models.sam.llmclient

SAM model of the ``LLMClient`` kind, generated from the Smarter platform's JSON Schema.

Do not edit: run ``scripts/generate_sam_models.py``. See :mod:`smarter.models.sam`.

.. py:class:: SAMDependency

   Bases: :class:`smarter.models.sam.base.SAMModel`

   A resource that depends on the resource that a manifest describes.

   .. py:attribute:: kind
      :type: str

      Kind[String]: The SAM kind of the resource that depends on this resource, e.g. LLMClient.

      Read only.


   .. py:attribute:: name
      :type: str

      Name[String]: The name of the resource that depends on this resource.

      Read only.



.. py:class:: SAMLLMClientCustomDomain

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest LLMClient.spec.config.customDomain.

   .. py:attribute:: aws_hosted_zone_id
      :type: str

      LLMClient.spec.configuration.customDomain.aws_hosted_zone_id[str].

      Required. The AWS hosted zone ID for this domain name. Example: Z08678681MEAGNEVHT5I8


   .. py:attribute:: domain_name
      :type: str

      LLMClient.spec.configuration.customDomain.domain_name[str].

      Required. The domain name. Example: example.com



.. py:class:: SAMLLMClientMetadata

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest - Metadata class.

   .. py:attribute:: annotations
      :type: None | list[dict[str, Union[str, int, float, bool, datetime.date, datetime.datetime, Annotated[str, StringConstraints(strip_whitespace=None, to_upper=None, to_lower=None, strict=None, min_length=None, max_length=None, pattern='^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$')], uuid.UUID, bytes, list, dict[str, Any]]]]

      The manifest annotations.

      Used for storing arbitrary metadata as
                  key-value pairs. Example: [{'smarter.sh/test-manifest/project-name': 'Scooby dooby do'}]. The
                  key should be a valid url-friendly string. The value accepts
                  multi-line string values (YAML block scalars) and various scalar types including
                  str, int, float, bool, datetime.date, datetime.datetime, decimal.Decimal, uuid.UUID, bytes, list, dict.


   .. py:attribute:: description
      :type: str | None

      The description for this resource.

      Be brief. Keep it under 255 characters.


   .. py:attribute:: name
      :type: str

      The camelCase name of the manifest resource.


   .. py:attribute:: tags
      :type: list[str] | None

      The tags of the manifest.

      Used for generic resource categorization and search. Example: ['tag1', 'tag2']


   .. py:attribute:: version
      :type: str | None

      The semantic version of the manifest.

      Example: 0.1.0



.. py:class:: SAMLLMClientSpecConfigPrompt

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest LLMClient.spec.config.prompt.

   What the LLMClient is and does: its LLM provider, model and system prompt, the text of its chat
   (its name, welcome message, example prompts and placeholder), and where it is published.

   .. py:attribute:: allowedOrigins
      :type: list[str] | None

      LLMClient.spec.configuration.prompt.allowed_origins[list[str]].

      Optional. The origins of the web pages that may call this llmclient from a browser, with the @smarter.sh/ui-chat React component, in addition to those that the Smarter platform allows. An origin is a scheme, a host and an optional port, without a path or a wildcard. Example: ['https://www.example.com', 'http://localhost:5173'].


   .. py:attribute:: appAssistant
      :type: str | None

      LLMClient.spec.configuration.prompt.app_assistant[str].

      Optional. The assistant name of the llmclient. Example: 'Joe'. This is the fictitious assistant name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appExamplePrompts
      :type: list[str] | None

      LLMClient.spec.configuration.prompt.app_example_prompts[list].

      Optional. A list of example prompts to add to new prompt sessions. These are intended to be brief, and the list is assumed to include only a few examples. Example: ['How do I get a refund?', 'What is the return policy?']. These are intended to help the user to understand the llmclient's capabilities. These will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appFileAttachment
      :type: bool | None

      LLMClient.spec.configuration.prompt.app_file_attachment[bool].

      Optional. Whether the llmclient supports file attachments. Defaults to False. When set to True, a file attachment button will be displayed in the prompt input box of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appInfoUrl
      :type: str | None

      LLMClient.spec.configuration.prompt.app_info_url[str].

      Optional. The custom info URL of the llmclient. This is a user control button located on the right-hand side of the header of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appName
      :type: str | None

      LLMClient.spec.configuration.prompt.app_name[str].

      Optional. The name of the llmclient. Example: 'Sales Support LLMClient'. This is the name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appPlaceholder
      :type: str | None

      LLMClient.spec.configuration.prompt.app_placeholder[str].

      Optional. The text placeholder added to the prompt input box for all new prompt sessions. Example: 'ask me anything...'. The place holder will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: appWelcomeMessage
      :type: str | None

      LLMClient.spec.configuration.prompt.app_welcome_message[str].

      Optional. The welcome message of the llmclient. Example: 'Welcome to Smarter's sales support llmclient!' The welcome messages will appear as the first assistant message in each message list from the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.


   .. py:attribute:: customDomain
      :type: smarter.models.sam.llmclient.SAMLLMClientCustomDomain | None

      LLMClient.spec.configuration.prompt.custom_domain[str].

      Optional. The custom domain to use for the llmclient. Example: example.com


   .. py:attribute:: defaultMaxTokens
      :type: Optional

      LLMClient.spec.configuration.prompt.default_max_tokens[int].

      Optional. The default max tokens to use for the llmclient. This defaults to 2048.
      The max tokens is an integer value that controls the maximum number of tokens in the llmclient's response. The maximum number of tokens is the sum of the tokens in the prompt and the tokens in the response. The maximum number of tokens varies by provider. Refer to vendor documentation as this value routinely changes as new models are released.


   .. py:attribute:: defaultModel
      :type: str | None

      LLMClient.spec.configuration.prompt.default_model[str].

      Optional. The default model to use for the llmclient. This changes routinely and is currently defaults to gpt-6-luna


   .. py:attribute:: defaultSystemRole
      :type: Optional

      LLMClient.spec.configuration.prompt.default_system_role[str].

      Optional. The default system prompt to use for the llmclient. This defaults to the following value:
      You are a helpful llmclient. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time..
      The system prompt is the first message in the conversation and is used to set the context for the llmclient. It is important to keep this prompt short, as it is included in the token count for each message. The maximum length of the system prompt is 2048 characters.


   .. py:attribute:: defaultTemperature
      :type: Optional

      LLMClient.spec.configuration.prompt.default_temperature[float].

      Optional. The default temperature to use for the llmclient. This defaults to 1.0.
      The temperature is a floating point value between 0 and 1 that controls the randomness of the llmclient's responses. A value of 0 means that the llmclient will always choose the most likely response, while a value of 1 means that the llmclient will choose a random response. Low values work better for information retrieval tasks, while high values work better for creative tasks.


   .. py:attribute:: deployed
      :type: bool | None

      LLMClient.spec.configuration.prompt.deployed[bool].

      Required. Whether the llmclient is deployed. Deployed means that the llmclient is available for use outside the Smarter Prompt Engineer Workbench. Published llmclients have their own subdomain, Kubernetes ingress, and TLS/SSL certificate.


   .. py:attribute:: provider
      :type: str | None

      LLMClient.spec.configuration.prompt.provider[str].

      Optional. The provider to use for the llmclient.


   .. py:attribute:: subdomain
      :type: str | None

      LLMClient.spec.configuration.prompt.subdomain[str].

      Optional. The subdomain to use for the llmclient for published public urls. Example: https://<subdomain>.3141-5926-5359.api.example.com



.. py:class:: AppBackgroundImageSize

   Bases: :class:`enum.Enum`

   LLMClient.styles.appBackgroundImageSize[str].

   Optional. How the background image fills the conversation: 'cover' (the default) fills it and crops the image's edges, 'contain' shows the whole image, and 'auto' shows the image at its own size, repeated like tiles.


.. py:class:: SAMLLMClientStatus

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest - Status class.

   .. py:attribute:: accountNumber
      :type: str

      LLMClient.status.account_number: The account owner of this LLMClient.

      Read only.


   .. py:attribute:: created
      :type: datetime

      The date in which this resource was created.

      Read only.


   .. py:attribute:: customUrl
      :type: str | None

      LLMClient.status.customUrl: The custom URL for this LLMClient.

      Read only.


   .. py:attribute:: defaultHost
      :type: str

      LLMClient.status.defaultHost: The default host URL for this LLMClient.

      Read only.


   .. py:attribute:: defaultUrl
      :type: str

      LLMClient.status.defaultUrl: The default URL for this LLMClient.

      Read only.


   .. py:attribute:: dependencies
      :type: list[smarter.models.sam.llmclient.SAMDependency] | None

      Dependencies[List]: The resources that depend on this resource, and that must be deleted, or stop referring to it, before it can be deleted.

      Lists only the resources that you can read. Read only.


   .. py:attribute:: deployed
      :type: bool

      LLMClient.status.deployed: Whether this LLMClient is currently deployed.

      Read only.


   .. py:attribute:: dnsVerificationStatus
      :type: str

      LLMClient.status.dnsVerificationStatus: The DNS verification status for this LLMClient.

      Read only.


   .. py:attribute:: hostname
      :type: str

      LLMClient.status.hostname: The hostname for this LLMClient.

      Read only.


   .. py:attribute:: modified
      :type: datetime

      The date in which this resource was most recently changed.

      Read only.


   .. py:attribute:: recordLocator
      :type: str

      RecordLocator[String]: An optional identifier used to locate the resource record associated with this manifest.

      Read only.


   .. py:attribute:: sandboxHost
      :type: str

      LLMClient.status.sandboxHost: The sandbox host URL for this LLMClient.

      Read only.


   .. py:attribute:: sandboxUrl
      :type: str

      LLMClient.status.sandboxUrl: The sandbox URL for this LLMClient.

      Read only.


   .. py:attribute:: url
      :type: str

      LLMClient.status.url: The URL for this LLMClient.

      Read only.


   .. py:attribute:: urlChatConfig
      :type: str

      LLMClient.status.urlChatConfig: The prompt config URL for this LLMClient.

      Read only.


   .. py:attribute:: urlChatapp
      :type: str

      LLMClient.status.urlChatapp: The chatapp URL for this LLMClient.

      Read only.


   .. py:attribute:: urlLLMClient
      :type: str

      LLMClient.status.urlLLMClient: The llmclient URL for this LLMClient.

      Read only.


   .. py:attribute:: username
      :type: str

      LLMClient.status.username: The Smarter user who created this LLMClient.

      Read only.



.. py:class:: SAMLLMClientStylesButtons

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.buttons``: the send and attach buttons, and the header's buttons.

   chatscope's ``Button``, class ``.cs-button``.

   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.buttons.color[str].

      Optional. The color of the buttons' icons. chatscope's $button-color. Example: '#6ea9d7'.



.. py:class:: SAMLLMClientStylesConversationHeader

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.conversationHeader``: the bar at the top of the chat.

   It holds the logo, the LLMClient's name, its model, and the buttons. chatscope's
   ``ConversationHeader``, class ``.cs-conversation-header``.

   .. py:attribute:: backgroundColor
      :type: str | None

      LLMClient.styles.conversationHeader.backgroundColor[str].

      Optional. The header's background color. chatscope's $conversation-header-bg-color. Example: '#1b1f3b'.


   .. py:attribute:: borderColor
      :type: str | None

      LLMClient.styles.conversationHeader.borderColor[str].

      Optional. The color of the line under the header. chatscope's $conversation-header-border-bottom. Example: '#ff5733'.


   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.conversationHeader.color[str].

      Optional. The color of the LLMClient's name. chatscope's $conversation-header-user-name-color. Example: '#ffffff'.


   .. py:attribute:: infoColor
      :type: str | None

      LLMClient.styles.conversationHeader.infoColor[str].

      Optional. The color of the line under the name, which names the LLM provider and model. chatscope's $conversation-header-info-color. Example: '#c0c4e0'.



.. py:class:: SAMLLMClientStylesMainContainer

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.mainContainer``: the frame around the whole chat.

   chatscope's ``MainContainer``, class ``.cs-main-container``.

   .. py:attribute:: backgroundColor
      :type: str | None

      LLMClient.styles.mainContainer.backgroundColor[str].

      Optional. The color behind the whole chat. chatscope's $main-container-bg-color. Example: '#ffffff'.


   .. py:attribute:: borderColor
      :type: str | None

      LLMClient.styles.mainContainer.borderColor[str].

      Optional. The color of the line around the chat. chatscope's $main-container-border. Example: '#ff5733'.


   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.mainContainer.color[str].

      Optional. The default text color of the chat. chatscope's $main-container-color. Example: '#212121'.



.. py:class:: SAMLLMClientStylesMessage

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.incomingMessage`` and ``outgoingMessage``: the message bubbles.

   Incoming messages are the assistant's, on the left. Outgoing messages are the user's, on the
   right. chatscope's ``Message``, classes ``.cs-message--incoming`` and ``.cs-message--outgoing``.

   .. py:attribute:: backgroundColor
      :type: str | None

      LLMClient.styles.message.backgroundColor[str].

      Optional. The bubble's color. chatscope's $message-content-incoming-bg-color and $message-content-outgoing-bg-color. Example: '#c6e3fa'.


   .. py:attribute:: borderColor
      :type: str | None

      LLMClient.styles.message.borderColor[str].

      Optional. The color of a thin line around the bubble, which has none by default. Example: '#6ea9d7'.


   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.message.color[str].

      Optional. The color of the text in the bubble. chatscope's $message-content-incoming-color and $message-content-outgoing-color. Example: '#212121'.


   .. py:attribute:: linkColor
      :type: str | None

      LLMClient.styles.message.linkColor[str].

      Optional. The color of links in the bubble. Example: '#0b57d0'.



.. py:class:: SAMLLMClientStylesMessageInput

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.messageInput``: the box at the bottom, in which the user types.

   chatscope's ``MessageInput``, class ``.cs-message-input``.

   .. py:attribute:: backgroundColor
      :type: str | None

      LLMClient.styles.messageInput.backgroundColor[str].

      Optional. The color of the strip around the box. chatscope's $message-input-bg-color. Example: '#ffffff'.


   .. py:attribute:: borderColor
      :type: str | None

      LLMClient.styles.messageInput.borderColor[str].

      Optional. The color of the line above the box. chatscope's $chat-container-message-input-border-top. Example: '#d1dbe3'.


   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.messageInput.color[str].

      Optional. The color of the text that the user types. chatscope's $message-input-content-editor-color. Example: '#212121'.


   .. py:attribute:: editorBackgroundColor
      :type: str | None

      LLMClient.styles.messageInput.editorBackgroundColor[str].

      Optional. The color of the box itself. chatscope's $message-input-content-editor-wrapper-bg-color. Example: '#c6e3fa'.


   .. py:attribute:: placeholderColor
      :type: str | None

      LLMClient.styles.messageInput.placeholderColor[str].

      Optional. The color of the placeholder, the hint in the empty box (spec.config.prompt.appPlaceholder). chatscope's $message-input-placeholder-color. Example: '#9e9e9e'.



.. py:class:: SAMLLMClientStylesMessageList

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.messageList``: the scrolling area that holds the conversation.

   It is painted over ``appBackgroundImageUrl``, so a semi-transparent ``backgroundColor`` tints the
   image. chatscope's ``MessageList``, class ``.cs-message-list``.

   .. py:attribute:: backgroundColor
      :type: str | None

      LLMClient.styles.messageList.backgroundColor[str].

      Optional. The color of the conversation's background. Over a background image, use a semi-transparent color, such as 'rgba(255, 255, 255, 0.6)', which tints the image. chatscope's $message-list-bg-color. Example: '#f6fbff'.


   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.messageList.color[str].

      Optional. The color of text in the conversation outside of the messages, such as the typing indicator's. chatscope's $message-list-color. Example: '#212121'.



.. py:class:: SAMLLMClientStylesTypingIndicator

   Bases: :class:`smarter.models.sam.base.SAMModel`

   ``spec.config.styles.typingIndicator``: "Assistant is typing", and its dots, while the LLM answers.

   chatscope's ``TypingIndicator``, class ``.cs-typing-indicator``.

   .. py:attribute:: color
      :type: str | None

      LLMClient.styles.typingIndicator.color[str].

      Optional. The color of the text and of the animated dots. chatscope's $typing-indicator-text-color and $typing-indicator-dot-bg-color. Example: '#6ea9d7'.



.. py:class:: SAMLLMClientSpecConfigStyles

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest LLMClient.spec.config.styles.

   The look of Smarter Chat for this LLMClient. Every setting is optional. See the module's docstring.

   .. py:attribute:: appBackgroundImageSize
      :type: smarter.models.sam.llmclient.AppBackgroundImageSize | None

      LLMClient.styles.appBackgroundImageSize[str].

      Optional. How the background image fills the conversation: 'cover' (the default) fills it and crops the image's edges, 'contain' shows the whole image, and 'auto' shows the image at its own size, repeated like tiles.


   .. py:attribute:: appBackgroundImageUrl
      :type: str | None

      LLMClient.styles.appBackgroundImageUrl[str].

      Optional. The url of an image that is displayed behind the conversation. Choose a quiet image, so that the messages stay readable, or tint it with a semi-transparent messageList.backgroundColor. Example: 'https://cdn.example.com/images/background.png'.


   .. py:attribute:: appLogoUrl
      :type: str | None

      LLMClient.styles.appLogoUrl[str].

      Optional. The url of the LLMClient's logo, a square image that is displayed in a circle at the left of the chat's header, and on the LLMClient's card in the web console. chatscope's Avatar. Example: 'https://cdn.example.com/images/logo.png'.


   .. py:attribute:: assistantAvatarUrl
      :type: str | None

      LLMClient.styles.assistantAvatarUrl[str].

      Optional. The url of a small square picture, displayed in a circle beside each of the assistant's messages. chatscope's Message Avatar. Example: 'https://cdn.example.com/images/assistant.png'.


   .. py:attribute:: borderRadius
      :type: str | None

      LLMClient.styles.borderRadius[str].

      Optional. How round the corners of the message bubbles and of the message input box are. '0' is square. chatscope's $default-border-radius. Example: '0.7em' (the default) or '18px'.


   .. py:attribute:: buttons
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesButtons | None

      LLMClient.styles.buttons[object].

      Optional. The chat's buttons.


   .. py:attribute:: conversationHeader
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesConversationHeader | None

      LLMClient.styles.conversationHeader[object].

      Optional. The bar at the top of the chat.


   .. py:attribute:: fontFamily
      :type: str | None

      LLMClient.styles.fontFamily[str].

      Optional. The chat's fonts, the first that the visitor's browser has, in order. chatscope's $default-font-family. Example: '"Fredoka", system-ui, sans-serif'.


   .. py:attribute:: fontSize
      :type: str | None

      LLMClient.styles.fontSize[str].

      Optional. The size of the chat's text, of which every other size is a proportion. chatscope's $main-container-font-size. Example: '16px' or '1.1rem'.


   .. py:attribute:: googleFont
      :type: str | None

      LLMClient.styles.googleFont[str].

      Optional. The name of a font from https://fonts.google.com, which the chat downloads. When fontFamily is not set, the chat uses this font. Example: 'Fredoka'.


   .. py:attribute:: incomingMessage
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesMessage | None

      LLMClient.styles.incomingMessage[object].

      Optional. The assistant's message bubbles, on the left.


   .. py:attribute:: mainContainer
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesMainContainer | None

      LLMClient.styles.mainContainer[object].

      Optional. The frame around the whole chat.


   .. py:attribute:: messageInput
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesMessageInput | None

      LLMClient.styles.messageInput[object].

      Optional. The box in which the user types.


   .. py:attribute:: messageList
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesMessageList | None

      LLMClient.styles.messageList[object].

      Optional. The area that holds the conversation.


   .. py:attribute:: outgoingMessage
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesMessage | None

      LLMClient.styles.outgoingMessage[object].

      Optional. The user's message bubbles, on the right.


   .. py:attribute:: typingIndicator
      :type: smarter.models.sam.llmclient.SAMLLMClientStylesTypingIndicator | None

      LLMClient.styles.typingIndicator[object].

      Optional. The indicator that the assistant is answering.


   .. py:attribute:: userAvatarUrl
      :type: str | None

      LLMClient.styles.userAvatarUrl[str].

      Optional. The url of a small square picture, displayed in a circle beside each of the user's messages. chatscope's Message Avatar. Example: 'https://cdn.example.com/images/user.png'.



.. py:class:: SAMLLMClientSpecConfig

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest LLMClient.spec.config.

   ``prompt``, which is required, configures the LLMClient, and ``styles``, which is optional, the
   look of its chat.

   Manifests written before the split have their settings directly in ``spec.config``. Apply
   rejects them, with an error that says where each setting belongs now. See
   :meth:`smarter.apps.llmclient.manifest.brokers.llmclient.SAMLLMClientBroker.raise_for_unknown_keys`.

   .. py:attribute:: prompt
      :type: SAMLLMClientSpecConfigPrompt

      LLMClient.spec.configuration.prompt[object].

      Required. The LLMClient's LLM provider, model and system prompt, the text of its chat, and where it is published.


   .. py:attribute:: styles
      :type: smarter.models.sam.llmclient.SAMLLMClientSpecConfigStyles | None

      LLMClient.spec.configuration.styles[object].

      Optional. The look of the LLMClient's chat, in the Smarter workbench and on every page that embeds it: its logo, background image, fonts and colors. See https://docs.smarter.sh/en/latest/smarter-resources/llmclient/styles.html



.. py:class:: SAMLLMClientSpec

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API LLMClient Manifest LLMClient.spec.

   .. py:attribute:: apiKey
      :type: str | None

      LLMClient.spec.apiKey[str].

      Optional. The name of the API key that this llmclient uses for authentication. Example: 'my_api_key'. API keys are only necessary for llmclients that are not public facing. This is the name of the API key that is used to authenticate the llmclient with the Smarter API. API keys are issued by a Smarter platform administrator and are used to authenticate the llmclient with the Smarter API.


   .. py:attribute:: config
      :type: SAMLLMClientSpecConfig

      LLMClient.spec.config[object].

      The configuration for the LLMClient.


   .. py:attribute:: functions
      :type: list[str] | None

      LLMClient.spec.functions[list].

      Optional. The built-in Smarter Functions to add to the LLMClient. Example: ['get_current_weather']. These are built-in backing functions written in Python that are fully compatible with OpenAI API-compatible function calling. These are not the same as OpenAI functions. See https://docs.smarter.sh/ for more information.


   .. py:attribute:: guardrails
      :type: list[str] | None

      LLMClient.spec.guardrails[list].

      Optional. The names of the Guardrails that protect the LLMClient's prompts. Example: ['pii_redaction_input', 'prompt_injection_keyword_input']. Each must be a Guardrail that you own, or that is shared with you, such as Smarter's built-in guardrails. Input guardrails run on the user's message before it is sent to the LLM, and output guardrails on the LLM's reply before it is returned to the user, in order of their priority. Experimental.


   .. py:attribute:: mcpClients
      :type: list[str] | None

      LLMClient.spec.mcpClients[list].

      Optional. The names of the MCPClients whose MCP servers' tools the LLMClient offers the LLM. Example: ['deepwiki']. Each must be an MCPClient that you own, or that is shared with you. Experimental.


   .. py:attribute:: plugins
      :type: list[str] | None

      LLMClient.spec.searchTerms[list].

      Optional. The Plugins to add to the LLMClient. Plugins are a proprietary extensibility model for tool calling and are not the same as OpenAI plugins. See https://docs.smarter.sh/plugins/ for more information.



.. py:class:: SAMLLMClient

   Bases: :class:`smarter.models.sam.base.SAMModel`

   Smarter API Manifest - LLMClient.

   .. py:attribute:: apiVersion
      :type: str

      ApiVersion[String]: Required.

      The API version of the AbstractSAMBase.


   .. py:attribute:: kind
      :type: str

      Kind[String]: Required.

      The kind of resource described by the manifest.


   .. py:attribute:: metadata
      :type: SAMLLMClientMetadata

      LLMClient.metadata[obj]: Required, the LLMClient metadata.


   .. py:attribute:: spec
      :type: SAMLLMClientSpec

      LLMClient.spec[obj]: Required, the LLMClient specification.


   .. py:attribute:: status
      :type: smarter.models.sam.llmclient.SAMLLMClientStatus | None

      LLMClient.status[obj]: Optional, Read-only.

      Stateful status information about the LLMClient.
