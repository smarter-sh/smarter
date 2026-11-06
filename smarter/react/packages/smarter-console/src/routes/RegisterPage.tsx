/**
 * The console's sign-up page: an email address and a password, which the backend checks with Django's
 * password validators. It exists only while the platform allows sign-up; otherwise it says so.
 */
import { gettext } from "@smarter/common";
import { useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError, TextField } from "@/components/FormFields";
import type { AccountErrors } from "@/contract.gen";
import { accountErrors, signUp } from "@/lib/account";
import { LOGIN_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

const NO_ERRORS: AccountErrors = { detail: "", fieldErrors: {} };

export function RegisterPage() {
  const { session, replace } = useConsoleSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<AccountErrors>(NO_ERRORS);
  const [submitting, setSubmitting] = useState(false);

  if (!session) return null;
  if (session.isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  if (!session.signIn.signUp) {
    return (
      <AuthCard title={gettext("Sign Up")}>
        <p className="text-center">{gettext("Registration is closed.")}</p>
        <p className="text-center mb-0">
          <Link to={LOGIN_PATH}>{gettext("Sign In")}</Link>
        </p>
      </AuthCard>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      replace(await signUp(session.cookies, { email, password }));
    } catch (e) {
      setErrors(accountErrors(e));
      setSubmitting(false);
    }
  }

  return (
    <AuthCard title={gettext("Sign Up")}>
      <form onSubmit={(event) => void handleSubmit(event)} noValidate>
        <FormError message={errors.detail} />
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
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          errors={errors.fieldErrors.password}
        />
        <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
          {gettext("Sign Up")}
        </button>
      </form>
      <p className="text-center text-gray-600 mt-6 mb-0">
        {gettext("Already have an account?")} <Link to={LOGIN_PATH}>{gettext("Sign In")}</Link>
      </p>
    </AuthCard>
  );
}
