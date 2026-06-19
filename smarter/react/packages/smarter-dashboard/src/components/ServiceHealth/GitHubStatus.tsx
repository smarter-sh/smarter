
export default function GitHubStatus() {
  return (
    <div className="row">
      <div className="col-4">
        <a target="_blank" rel="noopener noreferrer" href="https://github.com/smarter-sh/smarter/actions/workflows/build.yml">
          <img alt="Build Status" src="https://github.com/smarter-sh/smarter/actions/workflows/build.yml/badge.svg?branch=main" style={{ maxWidth: "100%" }} />
        </a>
      </div>
      <div className="col-4">
        <a target="_blank" rel="noopener noreferrer" href="https://github.com/smarter-sh/smarter/actions/workflows/deploy.yml">
          <img alt="Release Status" src="https://github.com/smarter-sh/smarter/actions/workflows/deploy.yml/badge.svg?branch=main" style={{ maxWidth: "100%" }} />
        </a>
      </div>
    </div>
  );
}
