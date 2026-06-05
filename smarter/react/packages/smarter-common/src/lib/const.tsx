import packageJson from "../../package.json" with { type: "json" };

export const packageName = packageJson.name;
export const packageVersion = packageJson.version;
export const loggerPrefix = `[Smarter ${packageName} v${packageVersion}]`;
