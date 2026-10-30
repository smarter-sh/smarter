import { useId, useState } from "react";

import { gettext } from "../../lib/i18n";

interface AnnotationSelectorBoxProps {
  /** Narrows the list by an annotation selector requirement, e.g. "acme.com/crm-id=A-1". */
  onAdd: (requirement: string) => void;
  /** Why the list api didn't apply the selector, or empty. */
  error: string;
}

/**
 * The annotation selector of a TabbedListView. A requirement is typed, then added with Enter, and
 * shows as a chip. The syntax is that of Kubernetes label selectors: "key" (the annotation exists),
 * "!key" (it doesn't), "key=value" and "key!=value". The list api validates it, and the error it
 * reports is shown under the box.
 */
export const AnnotationSelectorBox: React.FC<AnnotationSelectorBoxProps> = ({ onAdd, error }) => {
  const [value, setValue] = useState("");
  const errorId = useId();
  const add = () => {
    const requirement = value.trim();
    if (!requirement) return;
    onAdd(requirement);
    setValue("");
  };
  return (
    <div>
      <div className="position-relative">
        <i
          className="ki-outline ki-filter position-absolute top-50 translate-middle-y ms-3 text-muted"
          aria-hidden="true"
        />
        <input
          type="text"
          className={`form-control form-control-sm ps-9${error ? " is-invalid" : ""}`}
          placeholder={gettext("Annotation, e.g. acme.com/id=42")}
          aria-label={gettext("Filter by annotation")}
          title={gettext("key, !key, key=value or key!=value. Press Enter to add it.")}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add();
            }
          }}
        />
      </div>
      {error && (
        <div id={errorId} className="invalid-feedback d-block fs-8" role="alert" style={{ maxWidth: "24rem" }}>
          {error}
        </div>
      )}
    </div>
  );
};
