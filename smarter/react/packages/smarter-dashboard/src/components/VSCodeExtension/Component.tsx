/**
 * VSCodeExtension dashboard widget.
 *
 * This component renders a promotional card for the Smarter Manifest VS Code
 * extension: its main features, direct links to the Visual Studio Marketplace
 * listing and official documentation, its install count, and a mock editor
 * that shows the extension flagging a misspelled key in a manifest.
 *
 * :returns: A JSX fragment containing the VS Code extension call-to-action
 *     widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <VSCodeExtension />
 */
import "@/components/VSCodeExtension/styles.css";

const MARKETPLACE = "https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest";

const FEATURES = [
  "Validation as you type",
  "Quick fixes for misspelled keys",
  "Completion and hover help",
  "Apply and deploy from the editor",
];

function VSCodeExtension() {
  return (
    <>
      {/* begin::Download VS Code Extension widget 4 */}
      <div
        id="vscode-extension"
        aria-label="VS Code Extension"
        className="card border-transparent h-100 vscode-card"
        data-bs-theme="light"
      >
        {/* begin::Body */}
        <div className="card-body ps-xl-15">
          <div className="row g-7 align-items-center">
            {/* begin::Pitch */}
            <div className="col-md-6">
              {/* begin::Title */}
              <div className="fs-2x fw-bold text-white mb-2">
                Get the{" "}
                <span className="position-relative d-inline-block">
                  <a href={MARKETPLACE} className="vscode-title-link">
                    VS Code Extension
                  </a>
                  <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 vscode-underline"></span>
                </span>
              </div>
              <p className="text-gray-400 fs-6 mb-5">
                Write Smarter manifests with the same validation that{" "}
                <code className="vscode-inline">smarter apply</code> uses, before you apply them.
              </p>
              {/* end::Title */}
              {/* begin::Features */}
              <ul className="vscode-features" aria-label="Features">
                {FEATURES.map((feature) => (
                  <li key={feature}>
                    <span className="vscode-check">&#10003;</span>
                    {feature}
                  </li>
                ))}
              </ul>
              {/* end::Features */}
              {/* begin::Action */}
              <div className="d-flex flex-wrap align-items-center gap-2 mt-6">
                <a href={MARKETPLACE} target="_blank" className="btn btn-sm fw-semibold vscode-btn">
                  Install
                </a>
                <a
                  href="https://docs.smarter.sh/en/latest/smarter-framework/vs-code-extension.html"
                  target="_blank"
                  className="btn btn-sm btn-light fw-semibold"
                >
                  Documentation
                </a>
                <a href={MARKETPLACE} target="_blank" className="ms-2">
                  <img
                    src="https://vsmarketplacebadges.dev/installs-short/Querium.smarter-manifest.svg"
                    alt="Installs"
                  />
                </a>
              </div>
              {/* end::Action */}
            </div>
            {/* end::Pitch */}
            {/* begin::Editor */}
            <div className="col-md-6">
              <div className="vscode-editor" aria-label="Example manifest with a validation problem">
                <div className="vscode-editor-bar">
                  <span className="vscode-dot vscode-dot-red"></span>
                  <span className="vscode-dot vscode-dot-yellow"></span>
                  <span className="vscode-dot vscode-dot-green"></span>
                  <span className="vscode-tab">
                    <img src="/static/images/vs-code-logo.png" alt="" />
                    secret.yaml
                  </span>
                </div>
                <pre className="vscode-code">
                  <div>
                    <span className="vscode-ln">1</span>
                    <span className="vscode-key">apiVersion</span>: <span className="vscode-str">smarter.sh/v1</span>
                  </div>
                  <div>
                    <span className="vscode-ln">2</span>
                    <span className="vscode-key">kind</span>: <span className="vscode-str">Secret</span>
                  </div>
                  <div>
                    <span className="vscode-ln">3</span>
                    <span className="vscode-key">metadata</span>:
                  </div>
                  <div>
                    <span className="vscode-ln">4</span>
                    {"  "}
                    <span className="vscode-key">name</span>: <span className="vscode-str">openai_api_key</span>
                  </div>
                  <div>
                    <span className="vscode-ln">5</span>
                    {"  "}
                    <span className="vscode-key vscode-squiggle">descripton</span>:{" "}
                    <span className="vscode-str">The OpenAI API key</span>
                    <span className="vscode-hover" role="note">
                      Unknown key &apos;descripton&apos; in metadata. Did you mean &apos;description&apos;?
                    </span>
                  </div>
                  <div>
                    <span className="vscode-ln">6</span>
                    {"  "}
                    <span className="vscode-key">version</span>: <span className="vscode-str">1.0.0</span>
                  </div>
                  <div>
                    <span className="vscode-ln">7</span>
                    <span className="vscode-key">spec</span>:
                  </div>
                </pre>
              </div>
            </div>
            {/* end::Editor */}
          </div>
        </div>
        {/* end::Body */}
      </div>
      {/* end::Download VS Code Extension widget 4 */}
    </>
  );
}

export default VSCodeExtension;
