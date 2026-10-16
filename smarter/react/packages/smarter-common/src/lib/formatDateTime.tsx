/**
 * Formats a date string as either a date in the browser's locale, or a human-readable relative time
 * in the language of the page.
 *
 * @param value - The date string to format. If null/undefined/invalid, returns "-".
 * @param formatType - "date" for a localized date string, "relative" for a humanized elapsed time (default: "date").
 * @param referenceValue - Required for "relative" format; the reference date string to compare against.
 * @returns The formatted date string, "never" if the difference is less than 5 seconds, or "-" for invalid input.
 * @throws Error if formatType is "relative" and referenceValue is missing or invalid.
 *
 * @example
 *   formatDateTime("2024-05-19T12:00:00Z", "date");
 *   formatDateTime("2024-05-19T12:00:00Z", "relative", "2024-05-19T11:59:00Z");
 */
import { loggerPrefix } from "./const";
import { formatDistanceToNow, type Locale } from "date-fns";
import { enUS, es, fr, ptBR } from "date-fns/locale";

import { currentLanguage, gettext } from "./i18n";

/**
 * The date-fns locale of each language in Django's settings.LANGUAGES, for relative times such as
 * "3 minutes ago", by its lowercase language code. A regional variant that isn't here gets its
 * generic language, and a language that isn't here falls back to English.
 */
const DATE_FNS_LOCALES: Record<string, Locale> = {
  en: enUS,
  es,
  fr,
  "pt-br": ptBR,
};

/** The date-fns locale of a language code such as "pt-br", "pt-BR", "es-MX" or "fr". */
const dateFnsLocale = (language: string): Locale => {
  const code = language.toLowerCase();
  return DATE_FNS_LOCALES[code] ?? DATE_FNS_LOCALES[code.split("-")[0]] ?? enUS;
};

export const formatDateTime = (
  value: string | null | undefined,
  formatType: "date" | "relative" = "date",
  referenceValue: string | null | undefined = null,
) => {
  if (!value) {
    console.warn(loggerPrefix, `Invalid date value: ${value}`);
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    console.warn(loggerPrefix, `Invalid date value: ${value}`);
    return "-";
  }

  if ((formatType == "relative" && !referenceValue) || (referenceValue && isNaN(Date.parse(referenceValue)))) {
    throw new Error(
      `formatDateTime: referenceValue must be a valid date string when formatType is "relative". Received: "${referenceValue}"`,
    );
  }

  // for comparing an 'update' date to the 'create' date.
  // If the difference is less than 'a few' seconds, we'll assume it was never updated.
  if (formatType == "relative" && referenceValue) {
    const referenceDate = new Date(referenceValue);
    if (Number.isNaN(referenceDate.getTime())) {
      console.warn(loggerPrefix, `Invalid reference date value: ${referenceValue}`);
      return "-";
    }
    const secondsDifference = Math.abs((date.getTime() - referenceDate.getTime()) / 1000);
    if (secondsDifference < 5) {
      return gettext("never");
    } else {
      // generate a humanized elapsed time string like "3 minutes ago" or "last week"
      const result = formatDistanceToNow(date, {
        addSuffix: true,
        locale: dateFnsLocale(currentLanguage()),
      });
      return result;
    }
  }

  if (formatType === "date") {
    const result = date.toLocaleString(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      // hour: "2-digit",
      // minute: "2-digit",
    });
    return result;
  }

  // received an unsupported formatType
  throw new Error(`Unsupported format type: ${formatType}`);
};
