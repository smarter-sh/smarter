/**
 * The form of an extension's settings, generated from the settings that its pyproject.toml declares.
 *
 * A secret setting's value is never shown, or sent back by the api: the form shows whether it is
 * set, and the name of its Secret, and can replace it with a typed value, which the api saves in a
 * Secret, or with one of the platform admin's Secrets, or clear it.
 */
import { useState } from "react";

import { Spinner } from "@/components/common";
import { configureRequest, initialValue } from "@/lib/settings";
import type { SecretChoice } from "@/lib/settings";
import type { ConfigureRequest, ExtensionDetail, ExtensionSetting } from "@/lib/types";

type Props = {
  extension: ExtensionDetail;
  busy: boolean;
  onSave: (request: ConfigureRequest) => void;
};

export default function SettingsForm({ extension, busy, onSave }: Props) {
  // the form is keyed by the extension's settings, so its state starts from their current values.
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(extension.settings.map((setting) => [setting.name, initialValue(setting)])),
  );
  const [secrets, setSecrets] = useState<Record<string, SecretChoice>>(() =>
    Object.fromEntries(
      extension.settings
        .filter((setting) => setting.type === "secret")
        .map((setting) => [setting.name, { mode: "keep", value: "", secretId: "" } as SecretChoice]),
    ),
  );

  if (extension.settings.length === 0) return <p className="text-muted">{extension.displayName} has no settings.</p>;

  const request = configureRequest(extension.settings, values, secrets);
  const changed = Object.keys(request.values ?? {}).length + Object.keys(request.secrets ?? {}).length > 0;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSave(request);
      }}
    >
      {extension.settings.map((setting) => (
        <div className="mb-6" key={setting.name}>
          <label className="form-label fw-semibold" htmlFor={`setting-${setting.name}`}>
            {setting.name}
            {setting.required ? (
              <span className="text-danger ms-1" title="Required">
                *
              </span>
            ) : null}
          </label>
          {setting.type === "secret" ? (
            <SecretField
              setting={setting}
              extension={extension}
              choice={secrets[setting.name] ?? { mode: "keep", value: "", secretId: "" }}
              onChange={(choice) => setSecrets({ ...secrets, [setting.name]: choice })}
            />
          ) : (
            <ValueField
              setting={setting}
              value={values[setting.name] ?? initialValue(setting)}
              onChange={(value) => setValues({ ...values, [setting.name]: value })}
            />
          )}
          <div className="form-text">
            {setting.description}
            {setting.type !== "secret" && setting.default !== null && setting.default !== undefined
              ? ` Default: ${String(setting.default)}.`
              : ""}
          </div>
        </div>
      ))}
      <button type="submit" className="btn btn-primary" disabled={busy || !changed}>
        {busy ? <Spinner label="Saving" /> : null}
        Save settings
      </button>
    </form>
  );
}

/** The field of a setting that is not a secret, by its type. */
function ValueField({
  setting,
  value,
  onChange,
}: {
  setting: ExtensionSetting;
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}) {
  const id = `setting-${setting.name}`;
  if (setting.type === "boolean") {
    return (
      <div className="form-check form-switch">
        <input
          id={id}
          className="form-check-input"
          type="checkbox"
          role="switch"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
        />
      </div>
    );
  }
  if (setting.type === "choice") {
    return (
      <select id={id} className="form-select" value={String(value)} onChange={(event) => onChange(event.target.value)}>
        <option value="">
          {setting.default !== null && setting.default !== undefined ? `Default (${String(setting.default)})` : "---"}
        </option>
        {(setting.choices ?? []).map((choice) => (
          <option key={choice} value={choice}>
            {choice}
          </option>
        ))}
      </select>
    );
  }
  const type =
    setting.type === "integer" || setting.type === "float" ? "number" : setting.type === "url" ? "url" : "text";
  return (
    <input
      id={id}
      className="form-control"
      type={type}
      step={setting.type === "float" ? "any" : undefined}
      placeholder={setting.default !== null && setting.default !== undefined ? String(setting.default) : ""}
      value={String(value)}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

/** The field of a secret setting: keep it, type a new value, choose a Secret, or clear it. */
function SecretField({
  setting,
  extension,
  choice,
  onChange,
}: {
  setting: ExtensionSetting;
  extension: ExtensionDetail;
  choice: SecretChoice;
  onChange: (choice: SecretChoice) => void;
}) {
  const id = `setting-${setting.name}`;
  return (
    <>
      <div className="mb-2">
        {setting.isSet ? (
          <span className="badge badge-light-success">Set, from the Secret {setting.secretName}</span>
        ) : (
          <span className="badge badge-light-danger">Not set</span>
        )}
      </div>
      <select
        id={id}
        className="form-select mb-2"
        aria-label={`How to set ${setting.name}`}
        value={choice.mode}
        onChange={(event) => onChange({ ...choice, mode: event.target.value as SecretChoice["mode"] })}
      >
        <option value="keep">{setting.isSet ? "Keep the current value" : "Leave it unset"}</option>
        <option value="value">Type a new value</option>
        <option value="existing">Use one of the platform's Secrets</option>
        {setting.isSet ? <option value="clear">Clear it</option> : null}
      </select>
      {choice.mode === "value" ? (
        <input
          className="form-control"
          type="password"
          autoComplete="new-password"
          aria-label={`New value of ${setting.name}`}
          placeholder="Saved, encrypted, in a Secret; never shown again"
          value={choice.value}
          onChange={(event) => onChange({ ...choice, value: event.target.value })}
        />
      ) : null}
      {choice.mode === "existing" ? (
        <select
          className="form-select"
          aria-label={`Secret for ${setting.name}`}
          value={choice.secretId}
          onChange={(event) => onChange({ ...choice, secretId: event.target.value })}
        >
          <option value="">Choose a Secret</option>
          {extension.availableSecrets.map((secret) => (
            <option key={secret.id} value={String(secret.id)}>
              {secret.name}
            </option>
          ))}
        </select>
      ) : null}
    </>
  );
}
