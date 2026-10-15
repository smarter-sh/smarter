/**
 * The settings form's values, and the request that saves them.
 */
import type { ConfigureRequest, ExtensionSetting, SecretInput } from "@/lib/types";

export type SettingValue = string | number | boolean | null;
export type SecretChoice = { mode: "keep" | "value" | "existing" | "clear"; value: string; secretId: string };

/** The form value of a non-secret setting: its configured value, or "" for its default. */
export function initialValue(setting: ExtensionSetting): string | boolean {
  if (setting.type === "boolean") return Boolean(setting.value ?? setting.default ?? false);
  return setting.value === null || setting.value === undefined ? "" : String(setting.value);
}

/**
 * The request that saves the form: the settings that changed. An empty field resets a setting to
 * its default.
 */
export function configureRequest(
  settings: ExtensionSetting[],
  values: Record<string, string | boolean>,
  secrets: Record<string, SecretChoice>,
): ConfigureRequest {
  const request: { values: Record<string, SettingValue>; secrets: Record<string, SecretInput> } = {
    values: {},
    secrets: {},
  };
  for (const setting of settings) {
    if (setting.type === "secret") {
      const choice = secrets[setting.name];
      if (!choice || choice.mode === "keep") continue;
      if (choice.mode === "value" && choice.value) request.secrets[setting.name] = { value: choice.value };
      if (choice.mode === "existing" && choice.secretId)
        request.secrets[setting.name] = { secretId: Number(choice.secretId) };
      if (choice.mode === "clear") request.secrets[setting.name] = {};
      continue;
    }
    const value = values[setting.name];
    if (value === undefined || value === initialValue(setting)) continue;
    if (setting.type === "boolean") request.values[setting.name] = Boolean(value);
    else if (value === "") request.values[setting.name] = null;
    else if (setting.type === "integer" || setting.type === "float") request.values[setting.name] = Number(value);
    else request.values[setting.name] = String(value);
  }
  return request;
}
