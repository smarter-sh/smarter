/**
 * The sign-in pages' form controls: a labelled input with the api's errors for its field, and the form's own
 * error.
 */
import { useId, type InputHTMLAttributes } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** The api's messages for this field. */
  errors?: string[];
}

export function TextField({ label, errors = [], ...inputProps }: TextFieldProps) {
  const id = useId();
  const errorsId = `${id}-errors`;
  const invalid = errors.length > 0;
  return (
    <div className="mb-5">
      <label htmlFor={id} className="form-label fw-semibold">
        {label}
      </label>
      <input
        id={id}
        className={`form-control${invalid ? " is-invalid" : ""}`}
        aria-invalid={invalid}
        aria-describedby={invalid ? errorsId : undefined}
        {...inputProps}
      />
      {invalid && (
        <ul id={errorsId} className="invalid-feedback d-block list-unstyled mb-0">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The form's own error, read out by screen readers when it appears. */
export function FormError({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div role="alert" className="alert alert-danger py-3">
      {message}
    </div>
  );
}
