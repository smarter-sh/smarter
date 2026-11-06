/**
 * The page that asks for an email address, and sends a password reset link to it. The answer is the same
 * whether or not the address has an account.
 */
import { gettext } from "@smarter/common";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError, TextField } from "@/components/FormFields";
import type { AccountErrors } from "@/contract.gen";
import { accountErrors, requestPasswordReset } from "@/lib/account";
import { LOGIN_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

const NO_ERRORS: AccountErrors = { detail: "", fieldErrors: {} };

export function PasswordResetRequestPage() {
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
      const response = await requestPasswordReset(session.cookies, email);
      setSent(response.detail);
    } catch (e) {
      setErrors(accountErrors(e));
    }
    setSubmitting(false);
  }

  return (
    <AuthCard title={gettext("Forgot Password ?")}>
      {sent ? (
        <p role="status" className="text-center">
          {sent}
        </p>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)} noValidate>
          <p className="text-gray-600">{gettext("Enter your email to reset your password.")}</p>
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
            {gettext("Send the link")}
          </button>
        </form>
      )}
      <p className="text-center mt-6 mb-0">
        <Link to={LOGIN_PATH}>{gettext("Back to sign in")}</Link>
      </p>
    </AuthCard>
  );
}
