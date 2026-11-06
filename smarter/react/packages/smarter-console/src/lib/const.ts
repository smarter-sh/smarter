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

/** The page of an account that isn't active, which the social sign-in pipeline redirects to as well. */
export const INACTIVE_PATH = "/account/inactive";

/** The query parameter that carries the route to return to after signing in. */
export const NEXT_PARAMETER = "next";

/** The doodle of the day, which the sign-in pages show. See smarter.apps.doodle.api.v1. */
export const DOODLE_API_URL = "/api/v1/doodles/today/";

/** The plain scene that the doodle shows until the day's arrives. See smarter.apps.doodle.const.BASE_SCENE_STATIC_PATH. */
export const DOODLE_BASE_IMAGE_URL = "/static/doodle/base.svg";
