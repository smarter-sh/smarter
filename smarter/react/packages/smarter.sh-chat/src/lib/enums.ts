/**
 * The direction and the sender of a chat message.
 *
 * The roles are those of the OpenAI chat completion api, plus Smarter's own: "smarter" messages
 * describe what the Smarter backend did, e.g. which plugins it selected, and "smarter_error"
 * messages describe a failed prompt. See OpenAIMessageKeys in
 * smarter.apps.provider.services.text_completion.const.
 */
export const MessageDirectionEnum = {
  INCOMING: "incoming",
  OUTGOING: "outgoing",
} as const;

export type MessageDirection = (typeof MessageDirectionEnum)[keyof typeof MessageDirectionEnum];

export const SenderRoleEnum = {
  SYSTEM: "system",
  ASSISTANT: "assistant",
  USER: "user",
  TOOL: "tool",
  SMARTER: "smarter",
  SMARTER_ERROR: "smarter_error",
} as const;

export type SenderRole = (typeof SenderRoleEnum)[keyof typeof SenderRoleEnum];

/** The roles that the LLM provider accepts. Smarter's own messages are only displayed. */
export const ValidMessageRolesEnum: SenderRole[] = [
  SenderRoleEnum.SYSTEM,
  SenderRoleEnum.ASSISTANT,
  SenderRoleEnum.USER,
  SenderRoleEnum.TOOL,
];

/** The roles of the backend's messages, which the metadata toggle shows and hides. */
export const MetadataRolesEnum: SenderRole[] = [SenderRoleEnum.SMARTER, SenderRoleEnum.SYSTEM, SenderRoleEnum.TOOL];
