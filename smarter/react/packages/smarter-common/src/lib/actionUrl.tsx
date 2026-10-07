/**
 * The URL of a list view's API action, e.g. clone, rename or delete.
 *
 * A list app's session ApiUrl is its list endpoint, e.g.
 * /mcpclient/react-integration/api/listview/, and its actions are that endpoint's siblings, e.g.
 * /mcpclient/react-integration/api/clone/<id>/<new_name>/. See each Django app's urls.py.
 *
 * @param sessionContext - The session context, whose ApiUrl is the list endpoint.
 * @param path - The action's path, relative to the API, e.g. "clone/12/my_name/".
 * @returns The action's URL, e.g. /mcpclient/react-integration/api/clone/12/my_name/.
 *
 * Example:
 *   fetchDjangoUrl(sessionContext, actionUrl(sessionContext, `delete/${object.id}/`), JSON.stringify({}))
 */
import type { SessionContext } from "./Types";

export function actionUrl(sessionContext: SessionContext, path: string): string {
  return sessionContext.ApiUrl.replace(/listview\/?$/, "") + path;
}

export default actionUrl;
