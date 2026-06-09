
import packageJson from "../package.json" with { type: "json" };

export const projectName = packageJson.name;
export const projectVersion = packageJson.version;
export const loggerPrefix = `[Smarter ${projectName} v${projectVersion}]`;
