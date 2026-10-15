import packageJson from "../../package.json" with { type: "json" };

export const platformName = "Smarter";
export const projectName = packageJson.name;
export const projectVersion = packageJson.version;
export const loggerPrefix = `[${platformName} ${projectName} v${projectVersion}]`;
