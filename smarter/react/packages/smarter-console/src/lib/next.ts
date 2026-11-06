/** Where the console goes after signing in. */
import { NEXT_PARAMETER } from "@/lib/const";

/** The route to go to after signing in: the next parameter, if it is a path of this console, or home. */
export function nextRoute(searchParams: URLSearchParams): string {
  const next = searchParams.get(NEXT_PARAMETER) ?? "";
  // only a path of this console, never another site: "//evil.example" is a host, not a path.
  if (next.startsWith("/") && !next.startsWith("//")) {
    return next;
  }
  return "/";
}
