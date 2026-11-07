/**
 * Sessions, as GET /api/web/session/ returns them, for the stories and tests. src/contract.test.ts checks
 * them against the backend's schema, so that no test passes against data that the backend never sends.
 */
import type { ConsoleSession, ConsoleSidebar } from "@/contract.gen";

const branding: ConsoleSession["branding"] = {
  productName: "The Smarter Project",
  productDescription: "An open source, no-code AI authoring platform designed for instructional use.",
  corporateName: "The Smarter Project",
  corporateAddress: "",
  supportEmail: "support@example.com",
  supportPhoneNumber: "",
  supportHours: "",
  primaryContact: "",
  contactUrl: "https://example.com/contact/",
  copyright: "© 2023-2026 The Smarter Project. All rights reserved.",
  urlFacebook: "",
  urlTwitter: "",
  urlLinkedin: "",
  urlSlack: "",
  logoUrl: "https://cdn.example.com/images/logo/smarter-crop.png",
  marketingSiteUrl: "https://example.com/",
  projectWebsiteUrl: "https://smarter.sh",
  projectDocsUrl: "https://docs.smarter.sh",
  legalUrl: "https://example.com/legal",
  environmentUrl: "http://localhost:9357/",
};

/** What a visitor who isn't signed in gets. */
/** The sidebar's links of a user who isn't staff, on a platform without proxies, vectorstores or the terminal. */
export const userSidebar: ConsoleSidebar = {
  dashboard: "/dashboard/",
  promptPassthrough: "/dashboard/passthrough/",
  manifestDropZone: "/dashboard/dropzone/",
  terminal: null,
  providers: "/provider/",
  proxies: null,
  llmhost: "/llmhost/",
  llmhostcompute: "/llmhost/compute/",
  workbench: "/workbench/",
  orchestrators: "/orchestrator/",
  apiKeys: "/authtoken/",
  customDomains: "/llmclient/custom-domains/",
  extensions: "/extensions/",
  plugins: "/llm-tools/",
  mcpclients: "/mcpclient/",
  connections: "/connection/",
  vectorsearches: "/vectorsearch/",
  vectorstores: null,
  budgets: "/budget/",
  guardrails: "/guardrail/",
  secrets: "/secret/",
  exampleManifests: "/docs/manifests/",
  openapi: "/docs/openapi/",
  jsonSchemas: "/docs/json-schema/",
  infrastructureResources: null,
  admin: null,
};

export const visitorSession: ConsoleSession = {
  isAuthenticated: false,
  version: "0.42.11",
  branding,
  signIn: { google: true, github: false, signUp: true, footerLinks: false, doodle: false },
  language: {
    current: "en",
    bidi: false,
    languages: [
      { code: "en", name: "English" },
      { code: "es", name: "Español" },
    ],
  },
  cookies: { csrfCookieName: "csrftoken", sessionCookieName: "sessionid", cookieDomain: "localhost" },
  flags: {
    proxy: false,
    vectorstore: true,
    manifestDropZone: true,
    terminal: false,
    passthrough: true,
    serverLogs: true,
    didYouKnow: true,
    reactDebugMode: false,
  },
  samKinds: ["ApiConnection", "LLMClient", "Secret"],
  user: null,
  account: null,
  onboarding: null,
  welcome: null,
  badges: null,
  sidebar: null,
};

/** What a signed-in user gets. */
export const userSession: ConsoleSession = {
  ...visitorSession,
  isAuthenticated: true,
  user: {
    username: "ada",
    email: "ada@example.com",
    firstName: "Ada",
    lastName: "Lovelace",
    isSuperuser: false,
    isStaff: false,
    profileImageUrl: "/static/images/avatar.png",
    userProfileCount: 1,
  },
  account: { accountNumber: "3141-5926-5359", name: "Analytical Engines" },
  onboarding: { enabled: true, seen: [] },
  // closed, so that each page's test needn't answer its api: a test of the dialog opens it.
  welcome: { showAtStartup: true, show: false },
  badges: { extensionUpdates: 0 },
  sidebar: userSidebar,
};
