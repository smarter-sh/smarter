/**
 * The console's sign-in page.
 *
 * Until the console's own sign-in form arrives with the account endpoints of /api/web/account/, it sends the
 * visitor to the platform's sign-in page, which Django still serves. Django's session cookie then signs them
 * in to the console too. A signed-in user is sent on to the page they came for.
 */
import { gettext } from "@smarter/common";
import { Navigate, useSearchParams } from "react-router";

import { nextRoute } from "@/lib/next";
import { useConsoleSession } from "@/session/context";

export function LoginPage() {
  const { session } = useConsoleSession();
  const [searchParams] = useSearchParams();
  if (!session) return null;
  if (session.isAuthenticated) {
    return <Navigate to={nextRoute(searchParams)} replace />;
  }
  const signInUrl = new URL("login/", session.branding.environmentUrl).toString();
  return (
    <main className="d-flex flex-column align-items-center justify-content-center min-vh-100 gap-6">
      <img src={session.branding.logoUrl} alt="" height={64} />
      <h1 className="fs-2 fw-bold">{gettext("Sign In")}</h1>
      <a className="btn btn-primary" href={signInUrl}>
        {gettext("Sign in to Smarter")}
      </a>
    </main>
  );
}
