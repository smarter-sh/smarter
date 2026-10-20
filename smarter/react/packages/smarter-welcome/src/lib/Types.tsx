/**
 * Types of the welcome dialog: what main.tsx reads from the root element, and what the Django
 * welcome api returns. See smarter.apps.dashboard.views.views.api.welcome.
 */
import type { SessionContext } from "@smarter/common";

/** The links that the dialog's last step offers. See WelcomeUrls in the welcome api. */
export interface WelcomeUrls {
  /** The Prompt Workbench chat of the Get Weather example LLMClient, or null if the user can't read one. */
  weather: string | null;
  /** The Prompt Workbench's list of LLMClients. */
  llmclients: string;
  /** The documentation site, docs.smarter.sh. */
  docs: string;
  /** The Smarter project's website, smarter.sh. */
  project: string;
}

/** The response of the welcome api views. See WelcomeApiResponse in the welcome api. */
export interface WelcomeApiResponse {
  /** Whether the user has closed the welcome dialog with Show at startup unticked, so that it no longer opens by itself. */
  welcomed: boolean;
  urls: WelcomeUrls;
}

/** The root element's attributes. See templates/react/welcome.html. */
export interface AppContext {
  sessionContext: SessionContext;
  /** Returns the dialog's state and links. */
  apiUrl: string;
  /** Records that the user has been welcomed. */
  dismissApiUrl: string;
  /** Whether the dialog opens by itself on this page: it shows at startup, and hasn't been closed in this session. */
  show: boolean;
  /** Whether the dialog opens by itself each time the user signs in: its Show at startup box. */
  showAtStartup: boolean;
  /** The user's first name, or an empty string. */
  firstName: string;
  /** The Smarter logo. */
  logoUrl: string;
  /** The folder of the Keen dozzy-1 illustrations, ending in a slash. */
  illustrationsUrl: string;
}
