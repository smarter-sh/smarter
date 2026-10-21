/**
 * What a <smarter-chat> element renders in its shadow root: the chat, in the page ("inline" mode), or a button in a
 * corner of the page that opens and closes a panel with the chat ("launcher" mode).
 *
 * The launcher renders the chat only when it is first opened, so that a page view that never opens it never calls
 * the LLMClient, and keeps it rendered, but hidden, when it closes, so that the conversation is still there when it
 * opens again. The chat session is in a cookie for the whole website (cookiePath "/"), so the conversation also
 * follows the visitor from page to page.
 */
import { useEffect, useRef, useState } from "react";

import SmarterChat from "@/components/SmarterChat";
import { activateLanguage, gettext, interpolate } from "@/lib/i18n";
import type { EmbedOptions } from "./options";

export const PANEL_ID = "smarter-chat-embed-panel";

export interface EmbedAppProps {
  options: EmbedOptions;
  /** Whether the launcher is open. The element owns this state, so that page scripts can open and close it. */
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function Chat({ options }: { options: EmbedOptions }) {
  return (
    <SmarterChat
      key={options.chatbot}
      apiUrl={options.chatbot}
      apiKey={options.apiKey}
      toggleMetadata={false}
      debugMode={options.debug}
      streamProgress={options.streamProgress}
      sessionCookieName={options.sessionCookieName}
      debugCookieName={`${options.sessionCookieName}_debug`}
      cookiePath={options.cookiePath}
      language={options.language}
    />
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H8.4L4 21.5V18a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm3 6.5a1.5 1.5 0 1 0 0 .01Zm5 0a1.5 1.5 0 1 0 0 .01Zm5 0a1.5 1.5 0 1 0 0 .01Z"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
      <path
        fill="currentColor"
        d="M5.3 5.3a1 1 0 0 1 1.4 0L12 10.6l5.3-5.3a1 1 0 1 1 1.4 1.4L13.4 12l5.3 5.3a1 1 0 0 1-1.4 1.4L12 13.4l-5.3 5.3a1 1 0 0 1-1.4-1.4l5.3-5.3-5.3-5.3a1 1 0 0 1 0-1.4Z"
      />
    </svg>
  );
}

function Launcher({ options, open, onOpenChange }: EmbedAppProps) {
  // the launcher's labels are in the chat's language, and the chat is rendered only once it opens.
  activateLanguage(options.language);
  // Translators: the default accessible name of the button that opens the chat, and of its panel.
  const label = options.label ?? gettext("Chat");
  // the chat is rendered once the launcher has been opened, and stays rendered.
  const [opened, setOpened] = useState(open);
  if (open && !opened) setOpened(true);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    // Escape, anywhere in the chat, closes the panel, and returns the focus to the button.
    const panel = panelRef.current;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      onOpenChange(false);
      buttonRef.current?.focus();
    };
    panel?.addEventListener("keydown", handleKeyDown);
    return () => panel?.removeEventListener("keydown", handleKeyDown);
  }, [onOpenChange]);

  return (
    <div
      className={`smarter-chat-embed-launcher smarter-chat-embed-${options.position}`}
      style={{
        zIndex: options.zIndex,
        ["--smarter-chat-embed-width" as string]: options.width,
        ["--smarter-chat-embed-height" as string]: options.height,
      }}
    >
      {/* a region, rather than a dialog: it doesn't trap the focus, and the page stays usable while it's open. */}
      <section
        id={PANEL_ID}
        part="panel"
        className="smarter-chat-embed-panel"
        aria-label={label}
        hidden={!open}
        ref={panelRef}
      >
        {opened && <Chat options={options} />}
      </section>
      <button
        ref={buttonRef}
        type="button"
        part="launcher"
        className="smarter-chat-embed-button"
        style={{ background: options.color }}
        aria-label={open ? interpolate(gettext("Close %(label)s"), { label }) : label}

        aria-expanded={open}
        aria-controls={PANEL_ID}
        onClick={() => onOpenChange(!open)}
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </div>
  );
}

function EmbedApp(props: EmbedAppProps) {
  const { options } = props;
  if (options.mode === "launcher") return <Launcher {...props} />;
  return (
    <div part="chat" className="smarter-chat-embed-inline" style={{ width: options.width, height: options.height }}>
      <Chat options={options} />
    </div>
  );
}

export default EmbedApp;
