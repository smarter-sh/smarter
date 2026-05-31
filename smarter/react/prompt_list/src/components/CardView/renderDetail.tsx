/**
 * @file renderDetail.tsx
 * @module CardView/renderDetail
 *
 * Provides utilities for rendering labeled detail rows in CardView tables, supporting multiple data types.
 *
 * Exports:
 *   - DetailRowRenderer: Type definition for the row rendering function signature.
 *   - renderDetailRow: Function to render a table row for a given label, value, and data type.
 *
 * Usage:
 *   Use `renderDetailRow(label, value, dataType)` to generate a <tr> element for a details table in CardView.
 *   Handles formatting and rendering for different data types, including special handling for URLs, dates, JSON, and arrays.
 *
 * Example:
 *   renderDetailRow('Created At', '2024-05-24T12:00:00Z', 'dateTime')
 *   renderDetailRow('Website', 'https://example.com', 'url')
 *   renderDetailRow('Tags', ['tag1', 'tag2'], 'str[]')
 *
 * @author Smarter Team
 * @copyright Smarter, 2026
 */
import type { ReactNode } from "react";
import { loggerPrefix } from "@/const";

import { formatDateTime } from "@/lib/formatDateTime";

export type DetailRowRenderer = (
  label: string,
  value: unknown,
  dataType?: "string" | "url" | "dateTime" | "number" | "bool" | "json" | "str[]" | null,
  microHelp?: string | null,
) => ReactNode;

export const renderDetailRow: DetailRowRenderer = (label, value, dataType, microHelp) => {
  const colClasses = "w-25 prompt-list-detail-label";
  const dataClasses = "prompt-list-detail-value";
  const tdLabel = microHelp ? (
    <td className={colClasses}>
      {label}
      <sup className="text-danger" title={microHelp}>
        {" "}
        (*)
      </sup>
    </td>
  ) : (
    <td className={colClasses}>{label}</td>
  );

  if (value === null || value === undefined || value === "") {
    return (
      <tr>
        {tdLabel}
        <td className={dataClasses}>No value</td>
      </tr>
    );
  }

  let displayValue: React.ReactNode = (() => {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      return value;
    }
    if (value === null || value === undefined) {
      return "";
    }
    // For objects/arrays, stringify for display
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    return String(value);
  })();

  if (dataType === "dateTime") {
    if (typeof value === "string" || typeof value === "number") {
      displayValue = formatDateTime(String(value));
    } else {
      displayValue = "";
    }
  } else if (dataType === "url") {
    let linkText = "";
    if (typeof value === "string" || typeof value === "number") {
      linkText = String(value);
    } else if (typeof value === "object" && value !== null) {
      linkText = JSON.stringify(value);
    }
    const retElement = (
      <a href={String(value)} target="_blank" rel="noopener noreferrer">
        {linkText}
      </a>
    );
    return (
      <tr>
        {tdLabel}
        <td className={dataClasses}>{retElement}</td>
      </tr>
    );
  } else if (dataType === "number") {
    displayValue = Number(value);
  } else if (dataType === "bool") {
    displayValue = value ? "Yes" : "No";
  } else if (dataType === "json") {
    let jsonString = "";
    if (typeof value === "object") {
      jsonString = JSON.stringify(value, null, 2);
    } else {
      try {
        jsonString = JSON.stringify(JSON.parse(String(value)), null, 2);
      } catch (e) {
        jsonString = String(value); // fallback to raw string if parsing fails
      }
    }
    displayValue = <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{jsonString}</pre>;
  } else if (dataType === "str[]") {
    console.debug(loggerPrefix, "Rendering str[] value:", value);
    if (Array.isArray(value)) {
      displayValue = (
        <ul style={{ margin: 0, paddingLeft: "1.2em" }}>
          {value.map((item, idx) => (
            <li key={idx}>{String(item)}</li>
          ))}
        </ul>
      );
    } else {
      displayValue = String(value);
    }
  } else if (dataType === "string" || dataType === null || dataType === undefined) {
    // leave as is
  }

  return (
    <tr>
      {tdLabel}
      <td className={dataClasses}>{displayValue}</td>
    </tr>
  );
};
