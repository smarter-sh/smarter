/**
 * The page of an emailed activation link, /account/activate/<uidb64>/<token>/: it activates the account and
 * signs its user in, then goes on to the console. Signing in uses the link up, so a link that has been used,
 * or has expired, says so and offers a new one.
 */
import { gettext } from "@smarter/common";
import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError } from "@/components/FormFields";
import { accountErrors, activate } from "@/lib/account";
import { INACTIVE_PATH, LOGIN_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

export function ActivatePage() {
  const { session, replace } = useConsoleSession();
  const { uidb64 = "", token = "" } = useParams();
  const [error, setError] = useState("");
  // the link works once, so it is posted once, even when React runs the effect twice in development.
  const posted = useRef(false);
  const cookies = session?.cookies;
  const signedIn = session?.isAuthenticated ?? false;

  useEffect(() => {
    if (!cookies || signedIn || posted.current) return;
    posted.current = true;
    activate(cookies, uidb64, token).then(replace, (e: unknown) => setError(accountErrors(e).detail));
  }, [cookies, signedIn, uidb64, token, replace]);

  if (!session) return null;
  if (session.isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <AuthCard title={gettext("Activate your account")}>
      {error ? (
        <>
          <FormError message={error} />
          <p className="text-center">
            <Link to={INACTIVE_PATH}>{gettext("Send a new activation link")}</Link>
          </p>
        </>
      ) : (
        <p role="status" className="text-center">
          {gettext("Activating your account...")}
        </p>
      )}
      <p className="text-center mt-6 mb-0">
        <Link to={LOGIN_PATH}>{gettext("Back to sign in")}</Link>
      </p>
    </AuthCard>
  );
}
