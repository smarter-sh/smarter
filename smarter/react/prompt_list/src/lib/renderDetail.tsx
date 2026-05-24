
import type {DetailRowRenderer} from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";

export const renderDetailRow: DetailRowRenderer = (label, value, dataType) => {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const colClasses = "w-25 prompt-list-detail-label";
  const dataClasses = "prompt-list-detail-value";

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
        <td className={colClasses}>{label}</td>
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
  }
  else if (dataType === "string" || dataType === null || dataType === undefined) {
    // leave as is
  }

  return (
    <tr>
      <td className={colClasses}>{label}</td>
      <td className={dataClasses}>{displayValue}</td>
    </tr>
  );
};
