import packageJson from "../../package.json" with { type: "json" };

export const platformName = "Smarter";
export const projectName = packageJson.name;
export const projectVersion = packageJson.version;
export const loggerPrefix = `[${platformName} ${projectName} v${projectVersion}]`;

/** The documentation, and the other repositories, that the page links to. */
const DOCS = "https://docs.smarter.sh/en/latest";
export const DOCS_URLS = {
  apiKeys: `${DOCS}/smarter-platform/api-keys.html`,
  budgets: `${DOCS}/smarter-resources/smarter-budget.html`,
  llmclient: `${DOCS}/smarter-resources/smarter-llmclient.html`,
  wordpress: `${DOCS}/smarter-framework/smarter-wordpress.html`,
  drupal: `${DOCS}/smarter-framework/smarter-drupal.html`,
  shopify: `${DOCS}/smarter-framework/smarter-shopify.html`,
  reactInstallation: `${DOCS}/smarter-framework/smarter-chat/embedding.html#installation`,
  embedScript: `${DOCS}/smarter-framework/smarter-chat/embedding.html#the-embed-script`,
  gtm: `${DOCS}/smarter-framework/smarter-gtm.html`,
  docsSites: `${DOCS}/smarter-framework/smarter-docs-sites.html`,
  sdks: `${DOCS}/smarter-framework/apis-and-sdks.html`,
};

export const GITHUB_URLS = {
  organization: "https://github.com/smarter-sh",
  smarter: "https://github.com/smarter-sh/smarter",
  cli: "https://github.com/smarter-sh/smarter-cli",
  chat: "https://github.com/smarter-sh/smarter-chat",
  python: "https://github.com/smarter-sh/smarter-python",
  wordpressReleases: "https://github.com/smarter-sh/smarter-wordpress/releases",
  drupal: "https://github.com/smarter-sh/smarter-drupal",
  shopify: "https://github.com/smarter-sh/smarter-shopify",
};

export const NPM_PACKAGE_URL = "https://www.npmjs.com/package/@smarter.sh/ui-chat";
