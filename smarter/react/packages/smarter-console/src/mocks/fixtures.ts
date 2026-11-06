/**
 * Sessions, as GET /api/web/session/ returns them, for the stories and tests. src/contract.test.ts checks
 * them against the backend's schema, so that no test passes against data that the backend never sends.
 */
import type { ConsoleSession } from "@/contract.gen";

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
export const visitorSession: ConsoleSession = {
  isAuthenticated: false,
  version: "0.42.11",
  branding,
  signIn: { google: true, github: false, signUp: true, footerLinks: false, doodle: true },
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
  user: null,
  account: null,
  onboarding: null,
  welcome: null,
  badges: null,
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
  welcome: { showAtStartup: true, show: true },
  badges: { extensionUpdates: 0 },
};
