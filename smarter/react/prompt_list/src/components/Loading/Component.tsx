

export default function Loading() {
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
