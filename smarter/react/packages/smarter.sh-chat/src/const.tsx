import packageJson from "../package.json" with { type: "json" };

export const projectName = packageJson.name;
export const projectVersion = packageJson.version;
export const loggerPrefix = `[Smarter ${projectName} v${projectVersion}]`;

/** The default lifetime of the chat session and debug cookies: one day, in milliseconds. */
export const DEFAULT_COOKIE_EXPIRATION = 1000 * 60 * 60 * 24;
