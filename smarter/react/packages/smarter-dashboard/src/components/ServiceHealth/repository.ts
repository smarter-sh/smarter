/** Validation of the url of the platform's source code repository. */

/**
 * The url of a repository, normalized, or null if the value isn't a safe one to link to.
 *
 * Any host: the url comes from the platform's own ``git remote -v``. It must be https, without
 * credentials, a query or a fragment, and have a path of plain segments, such as
 * ``https://bitbucket.org/<owner>/<repo>``.
 */
export function repositoryUrl(value: string): string | null {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  const segments = url.pathname.split("/").filter(Boolean);
  if (url.protocol !== "https:" || segments.length === 0) return null;
  if (url.username || url.password || url.search || url.hash) return null;
  if (!segments.every((segment) => /^[\w.-]+$/.test(segment))) return null;
  return `https://${url.host}/${segments.join("/")}`;
}
