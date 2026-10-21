/**
 * The chat's title: the LLMClient's app name and version, with icons for whether it is valid, and
 * whether it is deployed or is still in the sandbox.
 */
import { gettext } from "@/lib/i18n";
import "@/components/AppTitle/styles.css";

interface AppTitleProps {
  title: string;
  isReady: boolean;
  isValid: boolean;
  isDeployed: boolean;
}

function Icon({ label, color, path }: { label: string; color: string; path: string }) {
  return (
    <svg className="smarter-chat-title-icon" viewBox="0 0 16 16" role="img" aria-label={label} fill={color}>
      <title>{label}</title>
      <path d={path} />
    </svg>
  );
}

const CHECK_CIRCLE =
  "M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0m-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z";
const X_CIRCLE =
  "M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293z";
const ROCKET =
  "M9.752 6.193c.599.6 1.73.437 2.528-.362s.96-1.932.362-2.531c-.599-.6-1.73-.438-2.528.361-.798.8-.96 1.933-.362 2.532M15.811 3.312c-.363 1.534-1.334 3.626-3.64 6.218l-.24 2.408a2.56 2.56 0 0 1-.732 1.526L8.817 15.85a.51.51 0 0 1-.867-.434l.27-1.899c.04-.28-.013-.593-.131-.956a9 9 0 0 0-.249-.657l-.082-.202c-.468-.07-.844-.393-1.162-.71-.319-.318-.64-.695-.71-1.163l-.202-.082a9 9 0 0 0-.657-.249c-.363-.118-.676-.172-.956-.131l-1.899.27a.51.51 0 0 1-.434-.867l2.391-2.391a2.56 2.56 0 0 1 1.526-.732l2.408-.24c2.592-2.306 4.684-3.277 6.218-3.64a.5.5 0 0 1 .6.6";

function AppTitle({ title, isReady, isValid, isDeployed }: AppTitleProps) {
  if (!isReady) {
    return <span>{gettext("Loading...")}</span>;
  }
  return (
    <span className="smarter-chat-title">
      {title}
      {isValid ? (
        // Translators: the LLMClient's manifest is valid.
        <Icon label={gettext("valid")} color="green" path={CHECK_CIRCLE} />
      ) : (
        <Icon label={gettext("not valid")} color="red" path={X_CIRCLE} />
      )}
      {isDeployed ? (
        // Translators: the LLMClient is deployed.
        <Icon label={gettext("deployed")} color="orange" path={ROCKET} />
      ) : (
        // Translators: the LLMClient is not deployed, and runs only in the sandbox.
        <span className="smarter-chat-title-sandbox">{gettext("(sandbox)")}</span>
      )}
    </span>
  );
}

export default AppTitle;
