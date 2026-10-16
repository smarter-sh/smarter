/**
 * Contribute dashboard widget.
 *
 * This component renders a dashboard contribution-focused card that encourages community
 * participation in the Smarter project: a few ways to help, the repository's activity
 * badges, links to the contributing guide and the open issues, and a supporting
 * illustration.
 *
 * :returns: A JSX fragment containing the contribution engagement widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Contribute />
 */
import "@/components/Contribute/styles.css";

const WAYS_TO_HELP = ["Fix a bug", "Improve the docs", "Write a test", "Build an extension"];

const BADGES = [
  {
    href: "https://github.com/smarter-sh/smarter/releases",
    src: "https://img.shields.io/github/v/release/smarter-sh/smarter?style=flat&color=ea580c",
    alt: "Latest Release",
  },
  {
    href: "https://github.com/smarter-sh/smarter/stargazers",
    src: "https://img.shields.io/github/stars/smarter-sh/smarter?style=flat&color=ea580c",
    alt: "GitHub Stars",
  },
  {
    href: "https://github.com/smarter-sh/smarter/network/members",
    src: "https://img.shields.io/github/forks/smarter-sh/smarter?style=flat&color=ea580c",
    alt: "GitHub Forks",
  },
];

function Contribute() {
  return (
    <>
      {/* begin::Engage widget 4 */}
      <section
        id="contribute"
        aria-label="Contribute"
        className="card border-transparent h-100 contribute-card"
        data-bs-theme="light"
      >
        {/* begin::Body */}
        <div className="card-body d-flex flex-column ps-xl-15 h-100 position-relative">
          {/* begin::Illustration */}
          <img
            src="/static/assets/media/illustrations/dozzy-1/13.png"
            className="position-absolute bottom-0 end-0 me-3 h-250px d-none d-md-block contribute-illustration"
            alt=""
          />
          {/* end::Illustration */}
          {/* begin::Title */}
          <div className="position-relative fs-2x fw-bold text-gray-900 mb-2 z-index-2">
            Contribute to{" "}
            <span className="position-relative d-inline-block">
              Smarter
              <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 contribute-underline"></span>
            </span>
          </div>
          <p className="text-gray-700 fs-6 mb-5 z-index-2 contribute-lede">
            Start small, learn by doing, and help improve Smarter while you discover how real Python projects work.
          </p>
          {/* end::Title */}
          {/* begin::Ways to help */}
          <ul className="contribute-chips z-index-2" aria-label="Ways to help">
            {WAYS_TO_HELP.map((way) => (
              <li key={way} className="contribute-chip">
                {way}
              </li>
            ))}
          </ul>
          {/* end::Ways to help */}
          {/* begin::Badges */}
          <ul className="contribute-badges z-index-2">
            {BADGES.map((badge) => (
              <li key={badge.alt}>
                <a href={badge.href} target="_blank" rel="noopener noreferrer">
                  <img src={badge.src} alt={badge.alt} />
                </a>
              </li>
            ))}
          </ul>
          {/* end::Badges */}
          {/* begin::Action */}
          <div className="mt-auto pt-7 z-index-2">
            <a
              href="https://docs.smarter.sh/en/latest/smarter-framework/guides/contributing.html"
              target="_blank"
              className="btn btn-sm fw-semibold me-2 contribute-btn"
            >
              Contributing guide
            </a>
            <a
              href="https://github.com/smarter-sh/smarter/issues"
              target="_blank"
              className="btn btn-sm btn-light fw-semibold"
            >
              Open issues
            </a>
          </div>
          {/* end::Action */}
        </div>
        {/* end::Body */}
      </section>
      {/* end::Engage widget 4 */}
    </>
  );
}

export default Contribute;
