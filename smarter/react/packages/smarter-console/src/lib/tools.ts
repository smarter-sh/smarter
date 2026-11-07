/**
 * The paths of the console's tool pages, and their apis. See routes/ToolPages and
 * smarter.apps.dashboard.views.dropzone, passthrough and terminal_emulator.
 */
export const DROPZONE_PATH = "/dashboard/dropzone";
export const PASSTHROUGH_PATH = "/dashboard/passthrough";
export const TERMINAL_PATH = "/dashboard/terminal";

export const toolUrls = {
  /** The cli api's apply, which the drop zone sends each dropped manifest to. */
  apply: "/api/v1/cli/apply/",
  /** The Prompt Passthrough's api, to which it appends the provider's name. */
  passthrough: "/api/v1/prompts/passthrough/",
  /** The providers and their models, for the Prompt Passthrough. */
  providers: "/api/web/dashboard/passthrough/providers/",
  /** The user's server log stream, for the Prompt Passthrough's Server Logs tab. */
  logStream: "/api/web/dashboard/logs/stream/",
  /** The ticket api, whose ticket opens the Terminal's WebSocket. */
  terminalTicket: "/api/web/dashboard/terminal/ticket/",
};
