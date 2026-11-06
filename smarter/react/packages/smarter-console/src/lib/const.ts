/** The console's constants. */
import packageJson from "../../package.json";

/** The client name and version that the console sends to the backend in its X-Smarter-* headers. */
export const projectName = packageJson.name;
export const projectVersion = packageJson.version;

/** The prefix of the console's own log messages. */
export const loggerPrefix = `[${projectName}]`;

/** The backend's session api, which tells the console who is using it. See smarter.apps.api.web.session. */
export const SESSION_API_URL = "/api/web/session/";

/** The console's sign-in route. */
export const LOGIN_PATH = "/login";

/** The query parameter that carries the route to return to after signing in. */
export const NEXT_PARAMETER = "next";
