/**
 * The web console session contract: generated from contract/console-session.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * What the web console needs to start, from GET /api/web/session/: the user, the account, the platform's branding, its sign-in options, features and languages, and the state of the welcome dialog and onboarding hints; and the requests and responses of its account api, /api/web/account/. Generated from smarter.apps.api.web.session.contract and smarter.apps.account.api.web.contract; do not edit.
 */
export interface SmarterWebConsoleSessionContract {
  [k: string]: unknown;
}
/**
 * A request that was refused, with why.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "AccountErrors".
 */
export interface AccountErrors {
  /**
   * Why, for the whole form, in the session's language.
   */
  detail: string;
  /**
   * The messages of each field that was refused, by its camelCase name; empty when none was.
   */
  fieldErrors: {
    [k: string]: string[];
  };
}
/**
 * A request that succeeded, with a message for the user.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "AccountMessage".
 */
export interface AccountMessage {
  /**
   * What happened, in the session's language.
   */
  detail: string;
}
/**
 * The body of ``POST /api/web/account/activation-resend/``.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ActivationResendRequest".
 */
export interface ActivationResendRequest {
  /**
   * The email address to send a new activation link to.
   */
  email: string;
}
/**
 * The account that the console acts for: that of the user's selected profile.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleAccount".
 */
export interface ConsoleAccount {
  /**
   * The account's number, e.g. 3141-5926-5359.
   */
  accountNumber: string;
  /**
   * The account's company name.
   */
  name: string;
}
/**
 * The counts that the sidebar shows beside its items.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleBadges".
 */
export interface ConsoleBadges {
  /**
   * Installed extensions with an update; 0 for a user who isn't a superuser.
   */
  extensionUpdates: number;
}
/**
 * The platform's identity and contacts, which the console shows in its header, footer and sign-in pages.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleBranding".
 */
export interface ConsoleBranding {
  /**
   * A page for contacting the organization.
   */
  contactUrl: string;
  /**
   * The copyright notice of the footer.
   */
  copyright: string;
  /**
   * Its postal address, on one line, or empty.
   */
  corporateAddress: string;
  /**
   * The organization that runs this platform.
   */
  corporateName: string;
  /**
   * This platform's own url, e.g. https://platform.example.com.
   */
  environmentUrl: string;
  /**
   * The legal page: terms, privacy and cookies.
   */
  legalUrl: string;
  /**
   * The logo, an absolute url on the project's CDN.
   */
  logoUrl: string;
  /**
   * The organization's website.
   */
  marketingSiteUrl: string;
  /**
   * The name of the platform's primary contact, or empty.
   */
  primaryContact: string;
  /**
   * A one-sentence description of the product.
   */
  productDescription: string;
  /**
   * The product's name, e.g. The Smarter Project.
   */
  productName: string;
  /**
   * The documentation, docs.smarter.sh.
   */
  projectDocsUrl: string;
  /**
   * The Smarter project's website.
   */
  projectWebsiteUrl: string;
  /**
   * The support email address, or empty.
   */
  supportEmail: string;
  /**
   * When support answers, or empty.
   */
  supportHours: string;
  /**
   * The support phone number, or empty.
   */
  supportPhoneNumber: string;
  /**
   * The organization's Facebook page, or empty.
   */
  urlFacebook: string;
  /**
   * The organization's LinkedIn page, or empty.
   */
  urlLinkedin: string;
  /**
   * An invitation to the project's Slack workspace, or empty.
   */
  urlSlack: string;
  /**
   * The organization's X/Twitter page, or empty.
   */
  urlTwitter: string;
}
/**
 * The names and domain of Django's cookies, which the console's api calls send.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleCookies".
 */
export interface ConsoleCookies {
  /**
   * The cookies' domain, or empty for the request's host.
   */
  cookieDomain: string;
  /**
   * The CSRF cookie, whose value is sent as X-CSRFToken.
   */
  csrfCookieName: string;
  /**
   * The session cookie.
   */
  sessionCookieName: string;
}
/**
 * The console's optional features: which pages exist, and which tabs and widgets show.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleFlags".
 */
export interface ConsoleFlags {
  /**
   * Whether the header shows a Did you know? tip.
   */
  didYouKnow: boolean;
  /**
   * Whether the manifest drop zone page exists.
   */
  manifestDropZone: boolean;
  /**
   * Whether the Prompt Passthrough page exists.
   */
  passthrough: boolean;
  /**
   * Whether the Proxies pages exist.
   */
  proxy: boolean;
  /**
   * Whether the React apps log their debugging output.
   */
  reactDebugMode: boolean;
  /**
   * Whether the Server Logs tabs show.
   */
  serverLogs: boolean;
  /**
   * Whether the Terminal page exists for this user, a superuser.
   */
  terminal: boolean;
  /**
   * Whether the Vectorstores pages exist.
   */
  vectorstore: boolean;
}
/**
 * The console's languages, and the one that this response, and the session, are in.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleLanguage".
 */
export interface ConsoleLanguage {
  /**
   * Whether the session's language is written right to left.
   */
  bidi: boolean;
  /**
   * The code of the session's language.
   */
  current: string;
  /**
   * Every language the menu offers.
   */
  languages: ConsoleLanguageOption[];
}
/**
 * A language that the console is translated into.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleLanguageOption".
 */
export interface ConsoleLanguageOption {
  /**
   * Its code, e.g. pt-br.
   */
  code: string;
  /**
   * Its name, in itself, e.g. Português Brasileiro.
   */
  name: string;
}
/**
 * The state of the console's onboarding hints for the user.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleOnboarding".
 */
export interface ConsoleOnboarding {
  /**
   * Whether hints show by themselves.
   */
  enabled: boolean;
  /**
   * The hints that the user has seen, which no longer show by themselves.
   */
  seen: string[];
}
/**
 * Everything that the console needs to start, for the request's user, or for a visitor who isn't signed in.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleSession".
 */
export interface ConsoleSession {
  /**
   * The account the console acts for, or null.
   */
  account: ConsoleAccount | null;
  /**
   * The sidebar's counts, or null.
   */
  badges: ConsoleBadges | null;
  branding: ConsoleBranding;
  cookies: ConsoleCookies;
  flags: ConsoleFlags;
  /**
   * Whether the request has a signed-in user.
   */
  isAuthenticated: boolean;
  language: ConsoleLanguage;
  /**
   * The onboarding hints' state, or null.
   */
  onboarding: ConsoleOnboarding | null;
  /**
   * Every SAM kind, sorted by name, e.g. LLMClient: the docs pages list each one's example manifest and JSON Schema.
   */
  samKinds: string[];
  /**
   * The sidebar's links, or null.
   */
  sidebar: ConsoleSidebar | null;
  signIn: ConsoleSignIn;
  /**
   * The signed-in user, or null.
   */
  user: ConsoleUser | null;
  /**
   * The platform's version.
   */
  version: string;
  /**
   * The welcome dialog's state, or null.
   */
  welcome: ConsoleWelcome | null;
}
/**
 * The urls of the sidebar's links, reversed by the backend.
 *
 * A link that the platform or the user doesn't have is null, and the sidebar leaves it out.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleSidebar".
 */
export interface ConsoleSidebar {
  /**
   * The Django admin, for a staff user.
   */
  admin: string | null;
  /**
   * The API Keys list.
   */
  apiKeys: string;
  /**
   * The Budgets list.
   */
  budgets: string;
  /**
   * The Connections list.
   */
  connections: string;
  /**
   * The Custom Domains list.
   */
  customDomains: string;
  /**
   * The dashboard.
   */
  dashboard: string;
  /**
   * The example manifests.
   */
  exampleManifests: string;
  /**
   * The Extensions console.
   */
  extensions: string;
  /**
   * The Guardrails list.
   */
  guardrails: string;
  /**
   * The Infrastructure Resources list, for a superuser.
   */
  infrastructureResources: string | null;
  /**
   * The SAM JSON Schemas.
   */
  jsonSchemas: string;
  /**
   * The LLM Hosts list.
   */
  llmhost: string;
  /**
   * The LLM Host Compute list.
   */
  llmhostcompute: string;
  /**
   * The manifest drop zone, while it is enabled.
   */
  manifestDropZone: string | null;
  /**
   * The MCP Clients list.
   */
  mcpclients: string;
  /**
   * The OpenAPI contract.
   */
  openapi: string;
  /**
   * The Orchestrators list.
   */
  orchestrators: string;
  /**
   * The LLM Tools list.
   */
  plugins: string;
  /**
   * The Prompt Passthrough, while it is enabled.
   */
  promptPassthrough: string | null;
  /**
   * The Providers list.
   */
  providers: string;
  /**
   * The Proxies list, while proxies are enabled.
   */
  proxies: string | null;
  /**
   * The Secrets list.
   */
  secrets: string;
  /**
   * The Terminal, for a superuser, while it is enabled.
   */
  terminal: string | null;
  /**
   * The Vectorsearches list.
   */
  vectorsearches: string;
  /**
   * The Vectorstores list, while vectorstores are enabled.
   */
  vectorstores: string | null;
  /**
   * The LLMClients list, the Prompt Engineer's Workbench.
   */
  workbench: string;
}
/**
 * The ways to sign in or sign up that the sign-in pages offer.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleSignIn".
 */
export interface ConsoleSignIn {
  /**
   * Whether the sign-in pages show the doodle of the day.
   */
  doodle: boolean;
  /**
   * Whether the sign-in page shows its footer's links.
   */
  footerLinks: boolean;
  /**
   * Whether the Sign in with GitHub button shows.
   */
  github: boolean;
  /**
   * Whether the Sign in with Google button shows.
   */
  google: boolean;
  /**
   * Whether anyone may create an account: the sign-up page answers 404 if not.
   */
  signUp: boolean;
}
/**
 * The signed-in user.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleUser".
 */
export interface ConsoleUser {
  email: string;
  firstName: string;
  isStaff: boolean;
  isSuperuser: boolean;
  lastName: string;
  /**
   * The user's avatar, or the default image.
   */
  profileImageUrl: string;
  /**
   * How many accounts the user belongs to.
   */
  userProfileCount: number;
  username: string;
}
/**
 * The state of the welcome dialog for the user.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "ConsoleWelcome".
 */
export interface ConsoleWelcome {
  /**
   * Whether it opens by itself now: it shows at startup, and hasn't been closed in this session.
   */
  show: boolean;
  /**
   * Whether the dialog opens by itself each time the user signs in.
   */
  showAtStartup: boolean;
}
/**
 * The body of ``POST /api/web/account/password-reset/<uidb64>/<token>/``.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "NewPasswordRequest".
 */
export interface NewPasswordRequest {
  /**
   * The new password, which Django's password validators must accept.
   */
  password: string;
  /**
   * The new password again.
   */
  passwordConfirm: string;
}
/**
 * The body of ``POST /api/web/account/password-reset-request/``.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "PasswordResetRequest".
 */
export interface PasswordResetRequest {
  /**
   * The email address to send the link to.
   */
  email: string;
}
/**
 * The body of ``POST /api/web/account/login/``.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "SignInRequest".
 */
export interface SignInRequest {
  /**
   * The email address.
   */
  email: string;
  /**
   * The password.
   */
  password: string;
}
/**
 * The body of ``POST /api/web/account/register/``.
 *
 * This interface was referenced by `SmarterWebConsoleSessionContract`'s JSON-Schema
 * via the `definition` "SignUpRequest".
 */
export interface SignUpRequest {
  /**
   * The email address, which is also the username.
   */
  email: string;
  /**
   * The password, which Django's password validators must accept.
   */
  password: string;
}
