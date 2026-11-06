/**
 * The page of an emailed password reset link, /password-reset-link/<uidb64>/<token>/: it checks the link,
 * asks for the new password twice, and sets it. Links in emails that were sent before the console moved here
 * keep working, because the path is the same.
 */
import { gettext } from "@smarter/common";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { FormError, TextField } from "@/components/FormFields";
import type { AccountErrors } from "@/contract.gen";
import { accountErrors, checkPasswordResetLink, resetPassword } from "@/lib/account";
import { LOGIN_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

const NO_ERRORS: AccountErrors = { detail: "", fieldErrors: {} };

type LinkState = "checking" | "valid" | "invalid";

export function PasswordResetPage() {
  const { session } = useConsoleSession();
  const { uidb64 = "", token = "" } = useParams();
  const [linkState, setLinkState] = useState<LinkState>("checking");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [errors, setErrors] = useState<AccountErrors>(NO_ERRORS);
  const [done, setDone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    checkPasswordResetLink(uidb64, token).then(
      () => setLinkState("valid"),
      (e: unknown) => {
        setErrors(accountErrors(e));
        setLinkState("invalid");
      },
    );
  }, [uidb64, token]);

  if (!session) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setSubmitting(true);
    setErrors(NO_ERRORS);
    try {
      const response = await resetPassword(session.cookies, uidb64, token, { password, passwordConfirm });
      setDone(response.detail);
    } catch (e) {
      setErrors(accountErrors(e));
    }
    setSubmitting(false);
  }

  let content;
  if (linkState === "checking") {
    content = <p role="status">{gettext("Loading...")}</p>;
  } else if (linkState === "invalid") {
    content = (
      <>
        <FormError message={errors.detail} />
        <p className="text-center">
          <Link to="/password-reset-request">{gettext("Send a new link")}</Link>
        </p>
      </>
    );
  } else if (done) {
    content = (
      <p role="status" className="text-center">
        {done}
      </p>
    );
  } else {
    content = (
      <form onSubmit={(event) => void handleSubmit(event)} noValidate>
        <FormError message={errors.detail} />
        <TextField
          label={gettext("New password")}
          type="password"
          name="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          errors={errors.fieldErrors.password}
        />
        <TextField
          label={gettext("Confirm the new password")}
          type="password"
          name="passwordConfirm"
          autoComplete="new-password"
          required
          value={passwordConfirm}
          onChange={(event) => setPasswordConfirm(event.target.value)}
          errors={errors.fieldErrors.passwordConfirm}
        />
        <button type="submit" className="btn btn-primary w-100" disabled={submitting}>
          {gettext("Set the new password")}
        </button>
      </form>
    );
  }

  return (
    <AuthCard title={gettext("Reset your password")}>
      {content}
      <p className="text-center mt-6 mb-0">
        <Link to={LOGIN_PATH}>{gettext("Back to sign in")}</Link>
      </p>
    </AuthCard>
  );
}
