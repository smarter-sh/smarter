/**
 * The Console's menu items: the manifest, the deployment, the configuration, the chat session's
 * tool calls, and the server logs.
 */
export const MenuItems = {
  MANIFEST: "manifest",
  DEPLOYMENT: "deployment",
  CHAT_CONFIG: "chat_config",
  CHAT_TOOL_CALL_HISTORY: "chat_tool_call_history",
  SERVER_LOGS: "server_logs",
} as const;

export type MenuItem = (typeof MenuItems)[keyof typeof MenuItems];

/**
 * The menu items that display the configuration's diagnostic parts, which the config api returns only
 * with ?verbose=true. The chat fetches them while one of these is selected, and the Console is shown.
 */
export const VERBOSE_MENU_ITEMS: readonly MenuItem[] = [MenuItems.CHAT_TOOL_CALL_HISTORY, MenuItems.CHAT_CONFIG];

/** The Console's first selected menu item: the server logs, when there are any, or the configuration. */
export function initialMenuItem(logStreamUrl: string | null | undefined): MenuItem {
  return logStreamUrl ? MenuItems.SERVER_LOGS : MenuItems.CHAT_CONFIG;
}
