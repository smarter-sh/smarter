
import { useLogStream } from './logStream';
import './styles.css';

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

      <section className="terminal-emulator">
         <div className="row">
           <div className="col-12">
             <h4>Logs</h4>
           </div>
         </div>
         {error && <p>Error: {error}</p>}
         <ul>
           {logs.map((log, index) => (
             <li key={index}>
               {log.timestamp && <span>{new Date(log.timestamp).toLocaleTimeString()} - </span>}
               {log.level && <span>[{log.level}] </span>}
               {log.logger && <span>{log.logger}: </span>}
               {log.message}
             </li>
           ))}
         </ul>
       </section>
     </>
   );
}

export default TerminalEmulator;
