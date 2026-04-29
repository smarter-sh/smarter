import { useLogStream } from "./logStream";
import "./styles.css";

interface TerminalEmulatorProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function TerminalEmulator({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
}: TerminalEmulatorProps) {
  const { logs, connected, error } = useLogStream(apiUrl);

  return (
    <>
      <section className="terminal-emulator">
        <div className="row">
          <div className="col-12">
            <h4>Terminal Emulator Component</h4>
            <p>apiUrl: {apiUrl}</p>
            <p>csrfCookieName: {csrfCookieName}</p>
            <p>djangoSessionCookieName: {djangoSessionCookieName}</p>
            <p>cookieDomain: {cookieDomain}</p>
            <p>csrftoken: {csrftoken}</p>
            <p>Connected: {connected ? "Yes" : "No"}</p>
          </div>
        </div>
      </section>


      <section className="terminal-window" aria-label="Log terminal">
        <div className="terminal-window__header">
          <div className="terminal-window__controls" aria-hidden="true">
            <span className="terminal-window__dot terminal-window__dot--close" />
            <span className="terminal-window__dot terminal-window__dot--minimize" />
            <span className="terminal-window__dot terminal-window__dot--maximize" />
          </div>
          <div className="terminal-window__title">logs@smarter:~</div>
          <div
            className={`terminal-window__status ${connected ? "is-online" : "is-offline"}`}
          >
            {connected ? "connected" : "disconnected"}
          </div>
        </div>

        <div className="terminal-window__body" role="log" aria-live="polite">
          {error && <p className="terminal-window__error">Error: {error}</p>}

          <ul className="terminal-window__list">
            {logs.map((log, index) => (
              <li
                key={`${log.timestamp ?? "log"}-${index}`}
                className="terminal-window__line"
                data-level={(log.level ?? "info").toLowerCase()}
              >
                {log.timestamp && (
                  <span className="terminal-window__timestamp">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                )}
                {log.level && (
                  <span className="terminal-window__level">[{log.level}]</span>
                )}
                {log.logger && (
                  <span className="terminal-window__logger">{log.logger}:</span>
                )}
                <span className="terminal-window__message">{log.message}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>{" "}
    </>
  );
}

export default TerminalEmulator;
