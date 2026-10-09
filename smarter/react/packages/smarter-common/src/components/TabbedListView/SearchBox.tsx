interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}

/**
 * The search of a TabbedListView. It only edits the search: the TabbedListView requests the
 * matching objects from its list api, which searches all of them, not only the current page's.
 */
export const SearchBox: React.FC<SearchBoxProps> = ({ value, onChange, placeholder }) => (
  <div className="position-relative">
    <i className="fas fa-search position-absolute top-50 translate-middle-y ms-3 text-muted" aria-hidden="true" />
    <input
      type="search"
      className="form-control form-control-sm ps-9"
      placeholder={placeholder}
      aria-label="Search"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  </div>
);
