/**
 * Formats a date string as either a localized date or a human-readable relative time.
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
import { formatDistanceToNow } from "date-fns";

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
      return "never";
    } else {
      // generate a humanized elapsed time string like "3 minutes ago" or "last week"
      const result = formatDistanceToNow(date, { addSuffix: true });
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
