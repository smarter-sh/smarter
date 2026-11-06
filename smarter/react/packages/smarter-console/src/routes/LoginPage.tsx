/**
 * The console's sign-in page: an email address and password, the Google and GitHub buttons when the platform
 * offers them, and links to sign up and to reset a password. A signed-in user is sent on to the page they came
 * for, which the next parameter names.
 */
import { gettext } from "@smarter/common";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useSearchParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError, TextField } from "@/components/FormFields";
import type { AccountErrors } from "@/contract.gen";
import { accountErrors, isInactiveAccount, signIn } from "@/lib/account";
import { INACTIVE_PATH } from "@/lib/const";
import { nextRoute } from "@/lib/next";
import { useConsoleSession } from "@/session/context";

const NO_ERRORS: AccountErrors = { detail: "", fieldErrors: {} };

/** The url that starts signing in with an OAuth provider, and comes back to the console's next route. */
function oauthUrl(backend: string, next: string): string {
  const query = new URLSearchParams({ next });
  return `/social-auth/login/${backend}/?${query.toString()}`;
}

export function LoginPage() {
  const { session, replace } = useConsoleSession();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<AccountErrors>(NO_ERRORS);
  const [inactive, setInactive] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!session) return null;
  const next = nextRoute(searchParams);
  if (session.isAuthenticated) {
    return <Navigate to={next} replace />;
  }
  const { signIn: options } = session;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setSubmitting(true);
    setErrors(NO_ERRORS);
    setInactive(false);
    try {
      replace(await signIn(session.cookies, { email, password }));
    } catch (e) {
      setErrors(accountErrors(e));
      // the right password of an account that isn't activated yet.
      setInactive(isInactiveAccount(e));
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title={gettext("Sign In")}>
      {(options.google || options.github) && (
        <div className="d-grid gap-3 mb-6">
          {options.google && (
            <a className="btn btn-light border" href={oauthUrl("google-oauth2", next)}>
              {gettext("Sign in with Google")}
            </a>
          )}
          {options.github && (
            <a className="btn btn-light border" href={oauthUrl("github", next)}>
              {gettext("Sign in with GitHub")}
            </a>
          )}
        </div>
      )}
      <form onSubmit={(event) => void handleSubmit(event)} noValidate>
        <FormError message={errors.detail} />
        {inactive && (
          <p className="text-center">
            <Link to={INACTIVE_PATH}>{gettext("Send a new activation link")}</Link>
          </p>
        )}
        <TextField
          label={gettext("Email")}
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          errors={errors.fieldErrors.email}
        />
        <TextField
          label={gettext("Password")}
          type="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          errors={errors.fieldErrors.password}
        />
        <div className="d-flex justify-content-end mb-6">
          <Link to="/password-reset-request">{gettext("Forgot Password ?")}</Link>
        </div>
        <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
          {gettext("Sign In")}
        </button>
      </form>
      {options.signUp && (
        <p className="text-center text-gray-600 mt-6 mb-0">
          {gettext("Not a Member yet?")} <Link to="/register">{gettext("Sign up")}</Link>
        </p>
      )}
    </AuthCard>
  );
}
