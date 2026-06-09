

export function Loading() {
  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: 40 }}>
      <div
        className="spinner-border text-primary"
        role="status"
        aria-label="Loading"
        style={{ width: 20, height: 20, borderWidth: 2 }}
      >
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  );
}

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, typically used in skeleton or ghost rows to indicate loading state.
 */
export const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
};
