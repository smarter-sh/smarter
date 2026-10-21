/**
 * McpServer dashboard widget.
 *
 * This component renders a promotional card for the Smarter Project MCP
 * Server, which every platform runs at ``/api/v1/mcp/smarter-project/``: a
 * read-only Model Context Protocol server, without authentication, that answers
 * questions about The Smarter Project from its own code and documentation. It
 * shows the command that adds this platform's server to Claude Code, its main
 * tools, and a link to its documentation.
 *
 * :param serverUrl: The MCP server's url, in the command. Defaults to this platform's, on the page's
 *     own domain. A page outside the web console, such as smarter.sh, passes a platform's absolute url.
 * :type serverUrl: str
 * :returns: A JSX fragment containing the MCP server call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <McpServer />
 *     <McpServer serverUrl="https://platform.smarter.sh/api/v1/mcp/smarter-project/" />
 */
import "./styles.css";
import { gettext, interpolateNodes } from "@smarter/common";

/** The server's path, on this platform's own domain. */
const MCP_SERVER_PATH = "/api/v1/mcp/smarter-project/";

const TOOLS = ["search_documentation", "search_code", "read_file"];

export interface McpServerProps {
  /** The MCP server's url, in the command. */
  serverUrl?: string;
}

/** This platform's server, on the page's own domain. Rendered without a browser, the path alone. */
const defaultServerUrl = () =>
  typeof window === "undefined" ? MCP_SERVER_PATH : `${window.location.origin}${MCP_SERVER_PATH}`;

function McpServer({ serverUrl = defaultServerUrl() }: McpServerProps) {
  return (
    <>
      <section id="mcp-server" aria-label={gettext("MCP Server")} className="card border-transparent h-100 mcp-card">
        <div className="card-body d-flex flex-column ps-xl-15 h-100">
          <span className="mcp-eyebrow">{gettext("Smarter MCP Server")}</span>
          <div className="fs-2x fw-bold mt-3 mb-2 mcp-headline">
            {/* Translators: a headline. %(span)s is its highlighted last words, translated separately. */}
            {interpolateNodes(gettext("Ask your %(span)s"), {
              span: (
                <span className="position-relative d-inline-block">
                  {/* Translators: the highlighted words of a headline. %(span)s is their decorative underline, and stays at the end. */}
                  {interpolateNodes(gettext("AI assistant%(span)s"), {
                    span: (
                      <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 mcp-underline"></span>
                    ),
                  })}
                </span>
              ),
            })}
          </div>
          <p className="fs-6 mb-5 mcp-lede">
            {gettext("This platform answers questions about itself from its own code and docs, for any MCP client.")}
          </p>
          <pre className="mcp-command" aria-label={gettext("Add this platform's MCP server to Claude Code")}>
            <span className="mcp-prompt">$ </span>claude mcp add --transport http smarter-project {serverUrl}
          </pre>
          <ul className="mcp-tools" aria-label={gettext("Tools")}>
            {TOOLS.map((tool) => (
              <li key={tool}>{tool}</li>
            ))}
          </ul>
          <div className="mt-auto pt-6">
            <a
              href="https://docs.smarter.sh/en/latest/smarter-platform/smarter-project-mcp-server.html"
              target="_blank"
              className="btn btn-sm fw-semibold mcp-btn"
            >
              {gettext("Documentation")}
            </a>
          </div>
        </div>
      </section>
    </>
  );
}

export default McpServer;
