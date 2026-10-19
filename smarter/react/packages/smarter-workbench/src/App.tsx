/**
 * The Prompt Engineer's Workbench: the chat with an LLMClient, Smarter Chat, from the @smarter.sh/ui-chat npm
 * package, and the developer Console beside it.
 *
 * The user resizes the chat and the Console by dragging the separator between them, and hides the Console, which
 * slides out to the right, with the Console button in the chat's header. The browser remembers both. In sandbox
 * mode, the chat's header also has a Docs button, which opens a dialog of links to the technical references. In
 * production mode, the chat displays only the conversation, as the LLMClient's users see it, and the Console, its
 * button and the Docs button are hidden. The Console's server logs follow the mode: DEBUG and above in sandbox mode,
 * and the server's own log level in production mode. A new chat clears them.
 *
 * The chat fetches the configuration's diagnostic parts (verbose) only while the Console displays them: in its Tool
 * Calls and Config tabs. When the Manifest tab's editor saves the manifest, the chat reloads the configuration.
 */
import { useCallback, useRef, useState } from "react";
import { gettext } from "@smarter/common";
import { HeaderButton, SmarterChat, type ChatConfig } from "@smarter.sh/ui-chat";
import { DEBUG_LOG_LEVEL } from "@smarter/serverlogs";

import Console from "@/components/Console";
import { initialMenuItem, VERBOSE_MENU_ITEMS, type MenuItem } from "@/components/Console/enums";
import DocsDialog from "@/components/DocsDialog";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ConsoleIcon, DocsIcon } from "@/components/icons";
import { useChatWidth, useConsoleVisible } from "@/lib/layout";
import type { WorkbenchConfig } from "@/lib/types";

export default function App({ workbench }: { workbench: WorkbenchConfig }) {
  const [config, setConfig] = useState<ChatConfig | null>(null);
  // the chat starts in sandbox mode when it has the mode toggle. onModeChange tells the workbench when it changes.
  const [sandbox, setSandbox] = useState(workbench.toggleMetadata);
  const [docsOpen, setDocsOpen] = useState(false);
  const [consoleVisible, setConsoleVisible] = useConsoleVisible();
  // counts the new chats, which clear the Console's server logs, and the saves of the manifest, which reload the
  // chat's configuration.
  const [chatCount, setChatCount] = useState(0);
  const [reloadKey, setReloadKey] = useState(0);
  const [consoleTab, setConsoleTab] = useState<MenuItem>(() => initialMenuItem(workbench.logStreamUrl));
  const containerRef = useRef<HTMLDivElement>(null);
  const { chatWidth, separatorProps } = useChatWidth(containerRef);

  // production mode, switched to with the chat's mode toggle, hides the Console and its button. The browser's
  // remembered visibility is kept, and restored on switching back to sandbox mode.
  const isProduction = workbench.toggleMetadata && !sandbox;
  const consoleShown = consoleVisible && !isProduction;
  const verbose = consoleShown && VERBOSE_MENU_ITEMS.includes(consoleTab);

  const handleNewChat = useCallback(() => setChatCount((count) => count + 1), []);
  const handleManifestSaved = useCallback(() => setReloadKey((key) => key + 1), []);

  const headerActions = (
    <>
      {sandbox && (
        <HeaderButton
          icon={<DocsIcon />}
          onClick={() => setDocsOpen(true)}
          title={gettext("Technical references for prompt engineers and software engineers")}
          aria-haspopup="dialog"
        >
          {/* Translators: the button that opens the dialog of links to the documentation. */}
          {gettext("Docs")}
        </HeaderButton>
      )}
      {!isProduction && (
        <HeaderButton
          className="smarter-workbench-console-toggle"
          icon={<ConsoleIcon visible={consoleVisible} />}
          onClick={() => setConsoleVisible((visible) => !visible)}
          title={consoleVisible ? gettext("Hide the Console") : gettext("Show the Console")}
          aria-label={gettext("Show the Console")}
          aria-pressed={consoleVisible}
        />
      )}
    </>
  );

  return (
    <div className="smarter-workbench" ref={containerRef}>
      <div
        className={`smarter-workbench-chat ${consoleShown ? "" : "smarter-workbench-chat-full"}`}
        style={consoleShown ? { flexBasis: `${chatWidth}%` } : undefined}
      >
        <SmarterChat
          apiUrl={workbench.apiUrl}
          toggleMetadata={workbench.toggleMetadata}
          csrfCookieName={workbench.csrfCookieName}
          sessionCookieName={workbench.sessionCookieName}
          cookieDomain={workbench.cookieDomain}
          debugMode={workbench.debugMode}
          smarterRequestId={workbench.smarterRequestId}
          verbose={verbose}
          reloadKey={reloadKey}
          headerActions={headerActions}
          onConfig={setConfig}
          onNewChat={handleNewChat}
          onModeChange={setSandbox}
        />
      </div>
      {consoleShown && <div className="smarter-workbench-separator" {...separatorProps} />}
      {/* hidden, rather than removed, so that the Console keeps its tab and its streamed logs, and so that it can
          slide out of view, and back. See styles.css. */}
      <div
        className={`smarter-workbench-console ${consoleShown ? "" : "smarter-workbench-console-hidden"}`}
        aria-hidden={!consoleShown}
        inert={!consoleShown}
      >
        <ErrorBoundary>
          <Console
            workbench={workbench}
            config={config}
            logLevel={sandbox ? DEBUG_LOG_LEVEL : null}
            resetKey={chatCount}
            onManifestSaved={handleManifestSaved}
            onSelect={setConsoleTab}
          />
        </ErrorBoundary>
      </div>
      {docsOpen && <DocsDialog onClose={() => setDocsOpen(false)} />}
    </div>
  );
}
