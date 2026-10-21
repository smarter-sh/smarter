/**
 * @smarter.sh/ui-chat: the public api of the npm package. See vite.config.ts (--mode lib).
 *
 * The Smarter web console's Prompt Engineer's Workbench imports it too, and puts its developer Console beside the
 * chat, with SmarterChat's verbose, reloadKey, headerActions and on* props.
 */

export { default as SmarterChat, HeaderButton } from "./components/SmarterChat";
export type { HeaderButtonProps } from "./components/SmarterChat";
export { MessageDirectionEnum, SenderRoleEnum, ValidMessageRolesEnum } from "./lib/enums";
export { projectVersion as version } from "./const";
export { CHAT_CONTRACT_V2_CAPABILITY, normalizeConfig } from "./lib/api";
export type { PromptProgressEvent } from "./lib/api";
export type {
  ApiMessage,
  ChatConfig,
  ChatHistory,
  ChatMessage,
  ChatMetaData,
  ChatbotConfig,
  Contract,
  LLMClientConfig,
  SmarterChatProps,
} from "./types";
