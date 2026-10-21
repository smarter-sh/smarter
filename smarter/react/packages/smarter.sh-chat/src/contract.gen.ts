/**
 * The Smarter Chat api contract: generated from contract/chat-contract.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "JsonValue".
 */
export type JsonValue = unknown;

/**
 * The requests and responses of the Smarter Chat configuration and prompt apis, versions 1 and 2. Generated from smarter.apps.prompt.contract.models; do not edit.
 */
export interface SmarterChatAPIContract {
  [k: string]: unknown;
}
/**
 * A message's audio part.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiAudioPart".
 */
export interface PromptChatApiAudioPart {
  input_audio: PromptChatApiInputAudio;
  type: "input_audio";
  [k: string]: unknown;
}
/**
 * The audio of an audio part: base64 encoded.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiInputAudio".
 */
export interface PromptChatApiInputAudio {
  data: string;
  format: "wav" | "mp3";
  [k: string]: unknown;
}
/**
 * @deprecated
 * The LLMClient, in version 1 of the configuration, whose keys are renamed: llmclient becomes chatbot.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiChatbotV1".
 */
export interface PromptChatApiChatbotV1 {
  app_assistant?: string | null;
  app_example_prompts?: string[] | null;
  app_file_attachment?: boolean | null;
  app_info_url?: string | null;
  app_name?: string | null;
  app_placeholder?: string | null;
  app_welcome_message?: string | null;
  default_model?: string | null;
  /**
   * The system prompt of a new chat session.
   */
  default_system_role?: string | null;
  deployed?: boolean | null;
  id: number;
  name: string;
  provider?: string | null;
  /**
   * The look of the chat: the manifest's spec.config.styles, with snake_case keys.
   */
  styles?: PromptChatApiStyles | null;
  /**
   * The number of the LLMClient's extensions, plugins and MCPClients.
   */
  total_tools?: number | null;
  /**
   * The url of the LLMClient's prompt api.
   */
  url_chatbot: string;
  version?: string | null;
  [k: string]: unknown;
}
/**
 * The look of the LLMClient's chat: its manifest's ``spec.config.styles``, with snake_case keys.
 *
 * Smarter Chat applies it as css custom properties. Every setting is optional, and one that is
 * left out keeps the chat's default.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiStyles".
 */
export interface PromptChatApiStyles {
  app_background_image_size?: ("cover" | "contain" | "auto") | null;
  app_background_image_url?: string | null;
  app_logo_url?: string | null;
  assistant_avatar_url?: string | null;
  border_radius?: string | null;
  buttons?: PromptChatApiStyleSection | null;
  conversation_header?: PromptChatApiStyleSection | null;
  font_family?: string | null;
  font_size?: string | null;
  google_font?: string | null;
  incoming_message?: PromptChatApiStyleSection | null;
  main_container?: PromptChatApiStyleSection | null;
  message_input?: PromptChatApiStyleSection | null;
  message_list?: PromptChatApiStyleSection | null;
  outgoing_message?: PromptChatApiStyleSection | null;
  typing_indicator?: PromptChatApiStyleSection | null;
  user_avatar_url?: string | null;
  [k: string]: unknown;
}
/**
 * A section of the LLMClient's styles: the colors of one of chatscope's components.
 *
 * A section has only the settings that its component has, in the manifest's
 * ``spec.config.styles``. See :mod:`smarter.apps.llmclient.manifest.models.llmclient.styles`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiStyleSection".
 */
export interface PromptChatApiStyleSection {
  background_color?: string | null;
  border_color?: string | null;
  color?: string | null;
  editor_background_color?: string | null;
  info_color?: string | null;
  link_color?: string | null;
  placeholder_color?: string | null;
  [k: string]: unknown;
}
/**
 * A choice of a chat completion.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiChoice".
 */
export interface PromptChatApiChoice {
  /**
   * e.g. stop, length or tool_calls.
   */
  finish_reason?: string | null;
  index?: number;
  message?: PromptChatApiMessage | null;
  [k: string]: unknown;
}
/**
 * A message, in the format of the OpenAI chat completion api.
 *
 * Smarter adds two roles, which are only displayed and never sent to an LLM: ``smarter``, a note
 * about what the backend did, and ``smarter_error``, a failed prompt's error.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiMessage".
 */
export interface PromptChatApiMessage {
  /**
   * The message's text, or its parts. Null for an assistant message that only calls tools.
   */
  content?:
    | string
    | (
        | PromptChatApiTextPart
        | PromptChatApiImagePart
        | PromptChatApiAudioPart
        | PromptChatApiFilePart
        | PromptChatApiRefusalPart
      )[]
    | null;
  /**
   * The name of a tool message's function.
   */
  name?: string | null;
  /**
   * system, assistant, user, tool, smarter or smarter_error.
   */
  role: string;
  /**
   * The tool call that a tool message answers.
   */
  tool_call_id?: string | null;
  /**
   * An assistant message's tool calls.
   */
  tool_calls?: PromptChatApiToolCall[] | null;
  [k: string]: unknown;
}
/**
 * A message's text part, in the format of the OpenAI chat completion api.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiTextPart".
 */
export interface PromptChatApiTextPart {
  text: string;
  type: "text";
  [k: string]: unknown;
}
/**
 * A message's image part.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiImagePart".
 */
export interface PromptChatApiImagePart {
  image_url: PromptChatApiImageUrl;
  type: "image_url";
  [k: string]: unknown;
}
/**
 * The image of an image part: an http(s) or base64 data url.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiImageUrl".
 */
export interface PromptChatApiImageUrl {
  detail?: ("auto" | "low" | "high") | null;
  url: string;
  [k: string]: unknown;
}
/**
 * A message's file part.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiFilePart".
 */
export interface PromptChatApiFilePart {
  file: PromptChatApiFileRef;
  type: "file";
  [k: string]: unknown;
}
/**
 * The file of a file part: its base64 data, or the id of an uploaded file.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiFileRef".
 */
export interface PromptChatApiFileRef {
  file_data?: string | null;
  file_id?: string | null;
  filename?: string | null;
  [k: string]: unknown;
}
/**
 * An assistant message's refusal part.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiRefusalPart".
 */
export interface PromptChatApiRefusalPart {
  refusal: string;
  type: "refusal";
  [k: string]: unknown;
}
/**
 * A tool call of an assistant message, in the format of the OpenAI chat completion api.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiToolCall".
 */
export interface PromptChatApiToolCall {
  function: PromptChatApiFunctionCall;
  id: string;
  type?: "function";
  [k: string]: unknown;
}
/**
 * The function that an assistant message calls.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiFunctionCall".
 */
export interface PromptChatApiFunctionCall {
  /**
   * The function's arguments, as a JSON string.
   */
  arguments: string;
  name: string;
  [k: string]: unknown;
}
/**
 * The LLM's chat completion, in the format of the OpenAI api, with only these fields.
 *
 * Smarter's own additions, ``smarter`` and ``metadata``, are not part of it: the messages, plugins and
 * tools are in :class:`PromptChatApiPromptResult`, and ``metadata``, which describes the tool calls
 * with their plugins' owners, is returned only to the cli.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiCompletion".
 */
export interface PromptChatApiCompletion {
  choices?: PromptChatApiChoice[];
  created?: number | null;
  id?: string | null;
  model?: string | null;
  object?: string | null;
  service_tier?: string | null;
  system_fingerprint?: string | null;
  usage?: PromptChatApiUsage | null;
  [k: string]: unknown;
}
/**
 * A chat completion's token usage.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiUsage".
 */
export interface PromptChatApiUsage {
  completion_tokens?: number | null;
  completion_tokens_details?: PromptChatApiTokenDetails | null;
  prompt_tokens?: number | null;
  prompt_tokens_details?: PromptChatApiTokenDetails | null;
  total_tokens?: number | null;
  [k: string]: unknown;
}
/**
 * The breakdown of a completion's tokens.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiTokenDetails".
 */
export interface PromptChatApiTokenDetails {
  audio_tokens?: number | null;
  cached_tokens?: number | null;
  reasoning_tokens?: number | null;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The parsed body of a successful prompt, version 1: a chat completion, with Smarter's additions.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiCompletionV1".
 */
export interface PromptChatApiCompletionV1 {
  smarter: PromptChatApiSmarterCompletionV1;
  [k: string]: unknown;
}
/**
 * @deprecated
 * Smarter's additions to a completion, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiSmarterCompletionV1".
 */
export interface PromptChatApiSmarterCompletionV1 {
  messages?: PromptChatApiMessage[];
  plugins?: string[];
  tools?: string[];
  [k: string]: unknown;
}
/**
 * The configuration, version 2.
 *
 * ``PromptConfigView.config()`` builds one, from which every response is derived:
 * :meth:`public` for a deployed LLMClient's own host, and :meth:`to_v1` for older clients.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiConfig".
 */
export interface PromptChatApiConfig {
  contract?: 2;
  /**
   * The ENABLE_REACTAPP_DEBUG_MODE waffle switch.
   */
  debug_mode: boolean;
  extensions?: PromptChatApiExtensionList | null;
  history: PromptChatApiHistory;
  llmclient: PromptChatApiLLMClient;
  meta_data: PromptChatApiMetaData;
  plugins: PromptChatApiPluginList;
  /**
   * True for a workbench url.
   */
  sandbox_mode: boolean;
  /**
   * The chat session's key.
   */
  session_key: string;
  [k: string]: unknown;
}
/**
 * The LLMClient's extensions.
 *
 * The list itself is returned only in the complete configuration, with ``?verbose=true``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiExtensionList".
 */
export interface PromptChatApiExtensionList {
  extensions?: PromptChatApiLLMClientExtension[];
  meta_data: PromptChatApiListMetaData;
  [k: string]: unknown;
}
/**
 * An extension of the LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientExtensions`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientExtension".
 */
export interface PromptChatApiLLMClientExtension {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * Whether the Extension is enabled, so that its tools are offered.
   */
  enabled: boolean;
  /**
   * LLMClientExtensions.extension: the Extension's id.
   */
  extension: number;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * LLMClientExtensions.llmclient: the LLMClient's id.
   */
  llmclient: number;
  /**
   * The Extension's slug, e.g. weather.
   */
  name: string;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
  /**
   * The Extension's installed version, e.g. 1.0.0.
   */
  version?: string | null;
}
/**
 * The counts of a list of the LLMClient's plugins or extensions.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiListMetaData".
 */
export interface PromptChatApiListMetaData {
  extensions_returned?: number | null;
  plugins_returned?: number | null;
  total_extensions?: number | null;
  total_plugins?: number | null;
  [k: string]: unknown;
}
/**
 * The chat session's history, in version 2.
 *
 * Only ``chat_history`` is public. ``prompt_tool_call_history`` is in the complete configuration with
 * ``?verbose=true``, and the other histories are returned only to the cli.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiHistory".
 */
export interface PromptChatApiHistory {
  /**
   * The session's messages, which restore the chat thread.
   */
  chat_history?: PromptChatApiMessage[];
  llmclient_request_history?: PromptChatApiLLMClientRequest[] | null;
  plugin_selector_history?: PromptChatApiPluginSelection[] | null;
  prompt_plugin_usage_history?: PromptChatApiPromptPluginUsage[] | null;
  prompt_tool_call_history?: PromptChatApiPromptToolCall[] | null;
}
/**
 * A request to the LLMClient's prompt api: a :class:`smarter.apps.llmclient.models.LLMClientRequests`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientRequest".
 */
export interface PromptChatApiLLMClientRequest {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * LLMClientRequests.is_aggregation.
   */
  is_aggregation?: boolean | null;
  /**
   * LLMClientRequests.llmclient: the LLMClient's id.
   */
  llmclient: number;
  /**
   * LLMClientRequests.request.
   */
  request?: PromptChatApiPromptRequest | null;
  /**
   * LLMClientRequests.session_key.
   */
  session_key?: string | null;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * The prompt api's request body: the chat thread, with only the roles that LLMs accept.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptRequest".
 */
export interface PromptChatApiPromptRequest {
  messages: PromptChatApiMessage[];
  session_key?: string | null;
  [k: string]: unknown;
}
/**
 * A plugin selector's activation: a :class:`smarter.apps.llmtool.models.PluginSelectorHistory`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPluginSelection".
 */
export interface PromptChatApiPluginSelection {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * PluginSelectorHistory.messages.
   */
  messages?: PromptChatApiMessage[] | null;
  /**
   * PluginSelectorHistory.plugin_selector: the PluginSelector's id.
   */
  plugin_selector: number;
  /**
   * PluginSelectorHistory.search_term.
   */
  search_term?: string | null;
  /**
   * PluginSelectorHistory.session_key.
   */
  session_key?: string | null;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * A plugin that the chat session used: a :class:`smarter.apps.prompt.models.PromptPluginUsage`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptPluginUsage".
 */
export interface PromptChatApiPromptPluginUsage {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * PromptPluginUsage.input_text.
   */
  input_text?: string | null;
  /**
   * PromptPluginUsage.plugin: the PluginMeta's id.
   */
  plugin: number;
  /**
   * PromptPluginUsage.prompt: the chat session's id.
   */
  prompt: number;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * A tool call of the chat session: a :class:`smarter.apps.prompt.models.PromptToolCall`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptToolCall".
 */
export interface PromptChatApiPromptToolCall {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * PromptToolCall.function_args.
   */
  function_args?: string | null;
  /**
   * PromptToolCall.function_name.
   */
  function_name?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * PromptToolCall.plugin: the PluginMeta's id, for a plugin.
   */
  plugin?: number | null;
  /**
   * PromptToolCall.prompt: the chat session's id.
   */
  prompt: number;
  request?: unknown;
  response?: unknown;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * The LLMClient, in version 2 of the configuration.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClient".
 */
export interface PromptChatApiLLMClient {
  app_assistant?: string | null;
  app_example_prompts?: string[] | null;
  app_file_attachment?: boolean | null;
  app_info_url?: string | null;
  app_name?: string | null;
  app_placeholder?: string | null;
  app_welcome_message?: string | null;
  default_model?: string | null;
  /**
   * The system prompt of a new chat session.
   */
  default_system_role?: string | null;
  deployed?: boolean | null;
  id: number;
  name: string;
  provider?: string | null;
  /**
   * The look of the chat: the manifest's spec.config.styles, with snake_case keys.
   */
  styles?: PromptChatApiStyles | null;
  /**
   * The number of the LLMClient's extensions, plugins and MCPClients.
   */
  total_tools?: number | null;
  /**
   * The url of the LLMClient's prompt api.
   */
  url_llmclient: string;
  version?: string | null;
  [k: string]: unknown;
}
/**
 * The LLMClient's state.
 *
 * The complete configuration, with ``?verbose=true``, adds the rest of ``LLMClientHelper.to_json()``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiMetaData".
 */
export interface PromptChatApiMetaData {
  /**
   * True if the LLMClient requires a Smarter api key, or a logged-in user.
   */
  is_authentication_required?: boolean | null;
  /**
   * True if the request's host is a custom domain.
   */
  is_custom_domain?: boolean | null;
  is_deployed?: boolean | null;
  is_valid?: boolean | null;
  ready?: boolean | null;
  [k: string]: unknown;
}
/**
 * The LLMClient's plugins.
 *
 * The list itself is returned only in the complete configuration, with ``?verbose=true``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPluginList".
 */
export interface PromptChatApiPluginList {
  meta_data: PromptChatApiListMetaData;
  plugins?: PromptChatApiLLMClientPlugin[];
  [k: string]: unknown;
}
/**
 * A plugin of the LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientPlugin`.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientPlugin".
 */
export interface PromptChatApiLLMClientPlugin {
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * LLMClientPlugin.llmclient: the LLMClient's id.
   */
  llmclient: number;
  plugin_meta: PromptChatApiPluginMeta;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * LLMClientPlugin.plugin_meta.
 */
export interface PromptChatApiPluginMeta {
  /**
   * MetaDataModel.annotations: a list of key-value pairs, or, in legacy rows, an object.
   */
  annotations?:
    | {
        [k: string]: JsonValue;
      }[]
    | {
        [k: string]: JsonValue;
      }
    | null;
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * MetaDataModel.description.
   */
  description?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * MetaDataModel.name, in snake_case.
   */
  name: string;
  /**
   * PluginMeta.plugin_class.
   */
  plugin_class: "api" | "skill" | "sql" | "static" | "websearch" | "imagesearch";
  /**
   * MetaDataModel.tags, by name.
   */
  tags?: string[];
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
  /**
   * MetaDataModel.version, e.g. 1.0.0.
   */
  version?: string | null;
}
/**
 * The configuration api's request body.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiConfigRequest".
 */
export interface PromptChatApiConfigRequest {
  /**
   * The chat session's key, or empty for a new session.
   */
  session_key?: string | null;
  [k: string]: unknown;
}
/**
 * The configuration api's response, version 2.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiConfigResponse".
 */
export interface PromptChatApiConfigResponse {
  /**
   * The api version, e.g. "smarter.sh/v1".
   */
  api: string;
  data: PromptChatApiConfig;
  metadata?: PromptChatApiJournalMetadata;
  [k: string]: unknown;
}
/**
 * The journal's command and thing.
 */
export interface PromptChatApiJournalMetadata {
  /**
   * The journal's command, e.g. prompt.
   */
  command?: string | null;
  /**
   * The journal's thing, e.g. LLMClient.
   */
  thing?: string | null;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The configuration api's response, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiConfigResponseV1".
 */
export interface PromptChatApiConfigResponseV1 {
  /**
   * The api version, e.g. "smarter.sh/v1".
   */
  api: string;
  data: PromptChatApiConfigV1;
  metadata?: PromptChatApiJournalMetadata1;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The configuration, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiConfigV1".
 */
export interface PromptChatApiConfigV1 {
  chatbot: PromptChatApiChatbotV1;
  /**
   * The ENABLE_REACTAPP_DEBUG_MODE waffle switch.
   */
  debug_mode: boolean;
  extensions?: PromptChatApiExtensionListV1 | null;
  history: PromptChatApiHistoryV1;
  meta_data: PromptChatApiMetaData;
  plugins: PromptChatApiPluginListV1;
  /**
   * True for a workbench url.
   */
  sandbox_mode: boolean;
  /**
   * The chat session's key.
   */
  session_key: string;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The LLMClient's extensions, in version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiExtensionListV1".
 */
export interface PromptChatApiExtensionListV1 {
  extensions?: PromptChatApiLLMClientExtensionV1[];
  meta_data: PromptChatApiListMetaData;
  [k: string]: unknown;
}
/**
 * @deprecated
 * An extension of the LLMClient, in version 1, whose ``llmclient`` is renamed ``chatbot``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientExtensionV1".
 */
export interface PromptChatApiLLMClientExtensionV1 {
  /**
   * LLMClientExtensions.llmclient: the LLMClient's id.
   */
  chatbot: number;
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  enabled: boolean;
  extension: number;
  /**
   * The row's primary key.
   */
  id: number;
  name: string;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
  version?: string | null;
}
/**
 * @deprecated
 * The chat session's history, in version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiHistoryV1".
 */
export interface PromptChatApiHistoryV1 {
  /**
   * The session's messages, which restore the chat thread.
   */
  chat_history?: PromptChatApiMessage[];
  chatbot_request_history?: PromptChatApiLLMClientRequestV1[] | null;
  plugin_selector_history?: PromptChatApiPluginSelection[] | null;
  prompt_plugin_usage_history?: PromptChatApiPromptPluginUsage[] | null;
  prompt_tool_call_history?: PromptChatApiPromptToolCall[] | null;
}
/**
 * @deprecated
 * A request to the LLMClient's prompt api, in version 1, whose ``llmclient`` is renamed ``chatbot``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientRequestV1".
 */
export interface PromptChatApiLLMClientRequestV1 {
  /**
   * LLMClientRequests.llmclient: the LLMClient's id.
   */
  chatbot: number;
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  is_aggregation?: boolean | null;
  request?: PromptChatApiPromptRequest | null;
  session_key?: string | null;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * @deprecated
 * The LLMClient's plugins, in version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPluginListV1".
 */
export interface PromptChatApiPluginListV1 {
  meta_data: PromptChatApiListMetaData;
  plugins?: PromptChatApiLLMClientPluginV1[];
  [k: string]: unknown;
}
/**
 * @deprecated
 * A plugin of the LLMClient, in version 1, whose ``llmclient`` is renamed ``chatbot``.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLLMClientPluginV1".
 */
export interface PromptChatApiLLMClientPluginV1 {
  /**
   * LLMClientPlugin.llmclient: the LLMClient's id.
   */
  chatbot: number;
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  plugin_meta: PromptChatApiPluginMeta1;
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
}
/**
 * A plugin's metadata: a :class:`smarter.apps.llmtool.models.PluginMeta`.
 *
 * Its owner is left out: the configuration never includes a user's profile.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPluginMeta".
 */
export interface PromptChatApiPluginMeta1 {
  /**
   * MetaDataModel.annotations: a list of key-value pairs, or, in legacy rows, an object.
   */
  annotations?:
    | {
        [k: string]: JsonValue;
      }[]
    | {
        [k: string]: JsonValue;
      }
    | null;
  /**
   * TimestampedModel.created_at.
   */
  created_at?: string | null;
  /**
   * MetaDataModel.description.
   */
  description?: string | null;
  /**
   * The row's primary key.
   */
  id: number;
  /**
   * MetaDataModel.name, in snake_case.
   */
  name: string;
  /**
   * PluginMeta.plugin_class.
   */
  plugin_class: "api" | "skill" | "sql" | "static" | "websearch" | "imagesearch";
  /**
   * MetaDataModel.tags, by name.
   */
  tags?: string[];
  /**
   * TimestampedModel.updated_at.
   */
  updated_at?: string | null;
  /**
   * MetaDataModel.version, e.g. 1.0.0.
   */
  version?: string | null;
}
/**
 * The journal's command and thing.
 */
export interface PromptChatApiJournalMetadata1 {
  /**
   * The journal's command, e.g. prompt.
   */
  command?: string | null;
  /**
   * The journal's thing, e.g. LLMClient.
   */
  thing?: string | null;
  [k: string]: unknown;
}
/**
 * The error of a failed request: the same shape for every error of the configuration and prompt apis.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiErrorBody".
 */
export interface PromptChatApiErrorBody {
  /**
   * A human-readable description, which Smarter Chat displays.
   */
  description: string;
  /**
   * The name of the error's class, e.g. NotFound or LLMProviderError.
   */
  errorClass: string;
  /**
   * The http status.
   */
  status: number;
  [k: string]: unknown;
}
/**
 * The body of an error response of the configuration or prompt apis, in both versions of the contract.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiErrorResponse".
 */
export interface PromptChatApiErrorResponse {
  api?: string | null;
  error: PromptChatApiErrorBody;
  metadata?: PromptChatApiJournalMetadata2 | null;
  [k: string]: unknown;
}
/**
 * The journal's record of a request, which every journaled response carries.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiJournalMetadata".
 */
export interface PromptChatApiJournalMetadata2 {
  /**
   * The journal's command, e.g. prompt.
   */
  command?: string | null;
  /**
   * The journal's thing, e.g. LLMClient.
   */
  thing?: string | null;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The parsed body of a failed prompt, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiFailureV1".
 */
export interface PromptChatApiFailureV1 {
  error: PromptChatApiProviderErrorV1;
  response: PromptChatApiCompletionV1;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The LLM provider's error, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiProviderErrorV1".
 */
export interface PromptChatApiProviderErrorV1 {
  message: string;
  status: number;
  [k: string]: unknown;
}
/**
 * @deprecated
 * A prompt's result, version 1: an AWS Lambda style response, whose body is a JSON string.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiLambdaResponseV1".
 */
export interface PromptChatApiLambdaResponseV1 {
  /**
   * A PromptChatApiCompletionV1, or a PromptChatApiFailureV1, as a JSON string.
   */
  body: string;
  headers?: {
    [k: string]: string;
  };
  isBase64Encoded?: boolean;
  statusCode: number;
  [k: string]: unknown;
}
/**
 * The data of a ``progress`` event: a step of a running prompt.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiProgressEvent".
 */
export interface PromptChatApiProgressEvent {
  /**
   * A short sentence, which Smarter Chat displays as is.
   */
  message: string;
  type:
    | "llm_request"
    | "tool_requested"
    | "tool_responded"
    | "plugin_called"
    | "mcp_tool_called"
    | "mcp_tool_responded"
    | "mcp_tool_failed";
  [k: string]: unknown;
}
/**
 * The data of the final ``result`` event.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiProgressResult".
 */
export interface PromptChatApiProgressResult {
  /**
   * Exactly the JSON of a non-streaming response.
   */
  response: PromptChatApiPromptResponse | PromptChatApiPromptResponseV1 | PromptChatApiErrorResponse;
  /**
   * The prompt's http status.
   */
  status: number;
  [k: string]: unknown;
}
/**
 * The prompt api's response, version 2.
 *
 * A failed prompt has ``error`` too, and its http status is the LLM provider's. Its ``data.messages``
 * include a ``smarter_error`` message, which is also saved in the session's history.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptResponse".
 */
export interface PromptChatApiPromptResponse {
  /**
   * The api version, e.g. "smarter.sh/v1".
   */
  api: string;
  data: PromptChatApiPromptResult;
  error?: PromptChatApiErrorBody | null;
  metadata?: PromptChatApiJournalMetadata3;
  [k: string]: unknown;
}
/**
 * The result of a prompt, version 2.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptResult".
 */
export interface PromptChatApiPromptResult {
  /**
   * The LLM's chat completion, in the format of the OpenAI api: its choices and usage.
   */
  completion?: PromptChatApiCompletion | null;
  contract?: 2;
  /**
   * The messages that the prompt added to the chat thread, in order.
   */
  messages?: PromptChatApiMessage[];
  /**
   * The plugins that Smarter selected.
   */
  plugins?: string[];
  /**
   * The prompt's http status: 200, or the LLM provider's error status.
   */
  status: number;
  /**
   * The functions that the LLM could call.
   */
  tools?: string[];
  [k: string]: unknown;
}
/**
 * The journal's record of a request, which every journaled response carries.
 */
export interface PromptChatApiJournalMetadata3 {
  /**
   * The journal's command, e.g. prompt.
   */
  command?: string | null;
  /**
   * The journal's thing, e.g. LLMClient.
   */
  thing?: string | null;
  [k: string]: unknown;
}
/**
 * @deprecated
 * The prompt api's response, version 1.
 *
 * This interface was referenced by `SmarterChatAPIContract`'s JSON-Schema
 * via the `definition` "PromptChatApiPromptResponseV1".
 */
export interface PromptChatApiPromptResponseV1 {
  /**
   * The api version, e.g. "smarter.sh/v1".
   */
  api: string;
  data: PromptChatApiLambdaResponseV1;
  metadata?: PromptChatApiJournalMetadata4;
  [k: string]: unknown;
}
/**
 * The journal's record of a request, which every journaled response carries.
 */
export interface PromptChatApiJournalMetadata4 {
  /**
   * The journal's command, e.g. prompt.
   */
  command?: string | null;
  /**
   * The journal's thing, e.g. LLMClient.
   */
  thing?: string | null;
  [k: string]: unknown;
}
