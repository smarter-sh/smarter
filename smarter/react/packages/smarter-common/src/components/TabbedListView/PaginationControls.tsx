import { useState } from "react";

import type { Pagination } from "../../lib/Types";

interface PageInputProps {
  page: number;
  numPages: number;
  disabled: boolean;
  onPage: (page: number) => void;
}

/**
 * The page number box. It goes to the page typed into it on Enter, or when it loses focus. A
 * page that is not a whole number from 1 to numPages is discarded. Its parent remounts it, by its
 * key, when the page changes, so that it shows the new page.
 */
function PageInput({ page, numPages, disabled, onPage }: PageInputProps) {
  const [draft, setDraft] = useState(String(page));
  const commit = () => {
    const requested = Number(draft);
    if (Number.isInteger(requested) && requested >= 1 && requested <= numPages && requested !== page) {
      onPage(requested);
    } else {
      setDraft(String(page));
    }
  };
  return (
    <input
      type="number"
      className="form-control form-control-sm text-center"
      style={{ width: "4.5rem" }}
      min={1}
      max={numPages}
      aria-label="Page number"
      disabled={disabled}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") commit();
      }}
    />
  );
}

interface PaginationControlsProps {
  pagination: Pagination;
  disabled: boolean;
  onPage: (page: number) => void;
}

/** The pager of a TabbedListView: what the page shows, the previous and next pages, and the page number box. */
export const PaginationControls: React.FC<PaginationControlsProps> = ({ pagination, disabled, onPage }) => {
  const { page, pageSize, numPages, count } = pagination;
  const first = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, count);
  return (
    <div className="d-flex flex-wrap gap-3 align-items-center justify-content-between p-3">
      <div className="text-muted fs-7" aria-live="polite">
        Showing {first.toLocaleString()}–{last.toLocaleString()} of {count.toLocaleString()}
      </div>
      <nav className="d-flex gap-2 align-items-center" aria-label="Pagination">
        <button
          type="button"
          className="btn btn-sm btn-light"
          aria-label="Previous page"
          title="Previous page"
          disabled={disabled || page <= 1}
          onClick={() => onPage(page - 1)}
        >
          <i className="fas fa-chevron-left" />
        </button>
        <span className="text-muted fs-7">Page</span>
        <PageInput key={page} page={page} numPages={numPages} disabled={disabled || numPages <= 1} onPage={onPage} />
        <span className="text-muted fs-7">of {numPages.toLocaleString()}</span>
        <button
          type="button"
          className="btn btn-sm btn-light"
          aria-label="Next page"
          title="Next page"
          disabled={disabled || page >= numPages}
          onClick={() => onPage(page + 1)}
        >
          <i className="fas fa-chevron-right" />
        </button>
      </nav>
    </div>
  );
};
