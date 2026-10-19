/** The data that the Console displays for each of its menu items. */
import type { ChatConfig } from "@smarter.sh/ui-chat";

import { MenuItems, type MenuItem } from "./enums";

/** The LLMClient's configuration, from its config api. Null until it loads. */
export type ConsoleConfig = ChatConfig | null;

/**
 * The JSON objects to display for a menu item. Null while the configuration has no data for it, e.g.
 * the tool calls, which the config api returns only with ?verbose=true, and which the chat is fetching.
 */
export function consoleData(config: ConsoleConfig, item: MenuItem): object[] | null {
  if (!config) return [];
  switch (item) {
    case MenuItems.CHAT_TOOL_CALL_HISTORY:
      return config.history.prompt_tool_call_history ?? null;
    case MenuItems.CHAT_CONFIG:
      return [config];
    default:
      // streamed (ServerLogs), or another component (ManifestTab, ArchitectureTab, DeploymentTab).
      return [];
  }
}
