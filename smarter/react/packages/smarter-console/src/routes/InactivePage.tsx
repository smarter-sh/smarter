/**
 * The page of an account that isn't active, /account/inactive/. Someone who signed up with a password
 * activates it with the link that the backend emailed them, and can ask for a new one here. An account that
 * signing in with Google or GitHub created waits for an administrator. The social sign-in pipeline redirects
 * here, and the sign-in and sign-up pages link here. The answer is the same whether or not the address has
 * an account that is waiting.
 */
import { gettext } from "@smarter/common";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError, TextField } from "@/components/FormFields";
import type { AccountErrors } from "@/contract.gen";
import { accountErrors, resendActivation } from "@/lib/account";
import { LOGIN_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

const NO_ERRORS: AccountErrors = { detail: "", fieldErrors: {} };

export function InactivePage() {
  const { session } = useConsoleSession();
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<AccountErrors>(NO_ERRORS);
  const [sent, setSent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!session) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      const response = await resendActivation(session.cookies, email);
      setSent(response.detail);
    } catch (e) {
      setErrors(accountErrors(e));
    }
    setSubmitting(false);
  }

  return (
    <AuthCard title={gettext("Your account isn't active")}>
      <p className="text-gray-600">
        {gettext("If you signed up with a password, follow the link that we emailed you to activate your account.")}
      </p>
      <p className="text-gray-600">
        {gettext("If you signed in with Google or GitHub, an administrator activates your account.")}
      </p>
      {sent ? (
        <p role="status" className="text-center">
          {sent}
        </p>
      ) : (
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
          <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
            {gettext("Send a new activation link")}
          </button>
        </form>
      )}
      <p className="text-center mt-6 mb-0">
        <Link to={LOGIN_PATH}>{gettext("Back to sign in")}</Link>
      </p>
    </AuthCard>
  );
}
