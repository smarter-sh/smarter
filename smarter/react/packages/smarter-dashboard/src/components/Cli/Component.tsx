/**
 * Cli dashboard widget.
 *
 * This component renders a dashboard call-to-action card for the Smarter
 * command-line interface, styled as a terminal window that shows a typical
 * session (install, configure, apply, deploy, list), followed by links to
 * download the CLI and open its documentation.
 *
 * :returns: A JSX fragment containing the CLI promotion widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <Cli />
 */
import "@/components/Cli/styles.css";

const SESSION = [
  { command: "brew install smarter", comment: "or apt, choco, docker" },
  { command: "smarter configure" },
  { command: "smarter apply -f llmclient.yaml" },
  { command: "smarter deploy llmclient customer_support" },
  { command: "smarter get llmclients" },
];

function Cli() {
  return (
    <>
      <section id="cli" aria-label="CLI" className="col-xl-4 mb-5 mb-xl-10">
        {/* begin::Engage widget 4 */}
        <div className="card border-transparent h-100 cli-card" data-bs-theme="light">
          {/* begin::Body */}
          <div className="card-body d-flex flex-column ps-xl-15 h-100">
            {/* begin::Title */}
            <div className="fs-2x fw-bold text-white mb-2">
              Smarter{" "}
              <span className="position-relative d-inline-block">
                CLI
                <span className="position-absolute opacity-50 bottom-0 start-0 border-4 border-success border-bottom w-100"></span>
              </span>
            </div>
            <p className="text-gray-400 fs-6 mb-7">Powerful tools for managing your AI resources.</p>
            {/* end::Title */}
            {/* begin::Terminal */}
            <div className="cli-terminal" aria-label="Example CLI session">
              <div className="cli-terminal-bar">
                <span className="cli-dot cli-dot-red"></span>
                <span className="cli-dot cli-dot-yellow"></span>
                <span className="cli-dot cli-dot-green"></span>
              </div>
              <pre className="cli-terminal-body">
                {SESSION.map((line) => (
                  <div key={line.command}>
                    <span className="cli-prompt">$ </span>
                    {line.command}
                    {line.comment && <span className="cli-comment"> # {line.comment}</span>}
                  </div>
                ))}
                <div>
                  <span className="cli-prompt">$ </span>
                  <span className="cli-cursor"></span>
                </div>
              </pre>
            </div>
            {/* end::Terminal */}
            {/* begin::Action */}
            <div className="mt-auto pt-7">
              <a href="https://smarter.sh/cli/" target="_blank" className="btn btn-sm btn-success fw-semibold me-2">
                Download
              </a>
              <a
                href="https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html"
                target="_blank"
                className="btn btn-sm btn-light fw-semibold"
              >
                Documentation
              </a>
            </div>
            {/* end::Action */}
          </div>
          {/* end::Body */}
        </div>
        {/* end::Engage widget 4 */}
      </section>
    </>
  );
}

export default Cli;
