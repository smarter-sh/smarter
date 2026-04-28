
import './styles.css';

interface TerminalEmulatorProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  defaultLLMProviderId: string | undefined;
  defaultTemplateId: string | undefined;
}

function TerminalEmulator({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
  defaultLLMProviderId,
  defaultTemplateId,
}: TerminalEmulatorProps) {

  return (
    <>
      <h4>Terminal Emulator Component</h4>
      <p>{apiUrl}</p>
      <p>{csrfCookieName}</p>
      <p>{csrftoken}</p>
      <p>{djangoSessionCookieName}</p>
      <p>{cookieDomain}</p>
      <p>{defaultLLMProviderId}</p>
      <p>{defaultTemplateId}</p>
    </>
  );
}

export default TerminalEmulator;
