import packageJson from "../../package.json" with { type: "json" };

export const platformName = "Smarter";
export const projectName = packageJson.name;
export const projectVersion = packageJson.version;
export const loggerPrefix = `[${platformName} ${projectName} v${projectVersion}]`;

/** The documentation that the page links to. */
export const DOCS = "https://docs.smarter.sh/en/latest";
export const DOCS_URLS = {
  manifests: `${DOCS}/smarter-framework/smarter-manifests.html`,
  dependencyTrees: `${DOCS}/smarter-framework/smarter-manifests/record-locators.html`,
  webConsole: `${DOCS}/smarter-platform/smarter-web-console.html`,
  llmclient: `${DOCS}/smarter-resources/smarter-llmclient.html`,
  ownership: `${DOCS}/smarter-resources/account/models/metadata_with_ownership.html`,
};
