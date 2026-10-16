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
 * :returns: A JSX fragment containing the MCP server call-to-action widget.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <McpServer />
 */
import "@/components/McpServer/styles.css";

/** The server's path, on this platform's own domain. */
const MCP_SERVER_PATH = "/api/v1/mcp/smarter-project/";

const TOOLS = ["search_documentation", "search_code", "read_file"];

function McpServer() {
  const serverUrl = `${window.location.origin}${MCP_SERVER_PATH}`;
  return (
    <>
      <section id="mcp-server" aria-label="MCP Server" className="card border-transparent h-100 mcp-card">
        <div className="card-body d-flex flex-column ps-xl-15 h-100">
          <span className="mcp-eyebrow">Smarter MCP Server</span>
          <div className="fs-2x fw-bold mt-3 mb-2 mcp-headline">
            Ask your{" "}
            <span className="position-relative d-inline-block">
              AI assistant
              <span className="position-absolute bottom-0 start-0 border-4 border-bottom w-100 mcp-underline"></span>
            </span>
          </div>
          <p className="fs-6 mb-5 mcp-lede">
            This platform answers questions about itself from its own code and docs, for any MCP client.
          </p>
          <pre className="mcp-command" aria-label="Add this platform's MCP server to Claude Code">
            <span className="mcp-prompt">$ </span>claude mcp add --transport http smarter-project {serverUrl}
          </pre>
          <ul className="mcp-tools" aria-label="Tools">
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
              Documentation
            </a>
          </div>
        </div>
      </section>
    </>
  );
}

export default McpServer;
