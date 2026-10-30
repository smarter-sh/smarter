import { gettext, interpolate } from "../../lib/i18n";

interface FilterChipProps {
  /** What narrows the list, e.g. "Tag: production". */
  label: string;
  /** Stops narrowing the list by it. */
  onRemove: () => void;
  /** The remove button's accessible name, "Remove <label>" by default. */
  removeLabel?: string;
}

/**
 * A chip that says what narrows a TabbedListView, with a button that removes it: the named filter,
 * a tag, or an annotation selector requirement.
 */
export const FilterChip: React.FC<FilterChipProps> = ({ label, onRemove, removeLabel }) => {
  // Translators: label says what narrows a list, e.g. "Tag: production".
  const buttonLabel = removeLabel ?? interpolate(gettext("Remove %(label)s"), { label });
  return (
    <span className="badge badge-light-primary fs-7 fw-semibold d-inline-flex align-items-center gap-2 py-2 ps-3 pe-2 text-break">
      {label}
      <button
        type="button"
        className="btn btn-icon btn-sm h-20px w-20px btn-active-light-primary"
        aria-label={buttonLabel}
        title={buttonLabel}
        onClick={onRemove}
      >
        <i className="ki-outline ki-cross fs-6 text-primary"></i>
      </button>
    </span>
  );
};
