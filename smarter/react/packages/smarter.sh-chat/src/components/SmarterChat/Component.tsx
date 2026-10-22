/**
 * SmarterChat: a chat with a Smarter LLMClient.
 *
 * It fetches the LLMClient's configuration, which includes the chat session's history, then sends
 * the chat thread to the LLMClient's prompt api with each new message, and adds the response's
 * messages to the thread. With verbose, the configuration's diagnostic parts, e.g. the session's tool
 * calls, are fetched too (with ?verbose=true), and again after each prompt. Failed prompts are
 * displayed in the thread, as "smarter_error" messages.
 * While a prompt runs, its progress (e.g. its tool calls and MCP server requests) is displayed in
 * the thread, with a spinner beside its current step, and is replaced by the response's messages
 * when it finishes. BANTER_DELAY_MS after a prompt is sent, the assistant replies with a chat bubble of silly
 * banter, with a twinkling sparkle, whose line changes every BANTER_INTERVAL_MS until the response replaces it.
 * See lib/banter.ts. Code blocks in messages
 * are syntax highlighted, and have a copy button.
 *
 * With toggleMetadata, the header has a Sandbox / Production mode switch. In sandbox mode, the
 * thread also displays Smarter's system, tool and meta data messages. In production mode, it displays
 * only the conversation, as the LLMClient's users see it. When the chat is narrow, the header's
 * buttons show only their icons. See styles.css.
 *
 * A page that hosts the chat, e.g. the Smarter web console's Prompt Engineer's Workbench, which puts
 * its developer Console beside it, follows it with onConfig, onNewChat and onModeChange, asks it to
 * reload its configuration with reloadKey, and adds its own buttons to the header with headerActions.
 *
 * The LLMClient's styles (its manifest's spec.config.styles) set its logo, which is displayed in
 * the header, its avatars, its background image, its fonts and its colors. See lib/styles.ts.
 *
 * The chat's own text, e.g. its buttons' labels, is in the language that the `language` prop asks for, or else the
 * page's, or else the browser's: English, Spanish or French. See lib/i18n.tsx. The LLMClient's own text, e.g. its
 * welcome message and its example prompts, and the messages of the conversation are displayed as they are.
 *
 */
import "@chatscope/chat-ui-kit-styles/dist/default/styles.min.css";
import {
  Avatar,
  Button,
  ChatContainer,
  ConversationHeader,
  MainContainer,
  Message,
  MessageInput,
  MessageList,
  TypingIndicator,
} from "@chatscope/chat-ui-kit-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ChangeEvent } from "react";

import { DEFAULT_COOKIE_EXPIRATION, loggerPrefix, projectName, projectVersion } from "@/const";
import { fetchConfig, fetchPrompt, type PromptProgressEvent } from "@/lib/api";
import { BANTER_DELAY_MS, BANTER_INTERVAL_MS, idleBanter } from "@/lib/banter";
import { copyCodeBlock } from "@/lib/code";
import { pastePlainText } from "@/lib/paste";
import { activateLanguage, gettext, interpolate, ngettext, pgettext } from "@/lib/i18n";
import { renderMermaidDiagrams, toggleMermaidDiagram } from "@/lib/mermaid";
import { cookieMetaFactory, setCookie } from "@/lib/cookie";
import { MetadataRolesEnum, SenderRoleEnum } from "@/lib/enums";
import { safeImageUrl, styleVariables, useGoogleFont } from "@/lib/styles";
import {
  chatInit,
  chatMessages2RequestMessages,
  messageFactory,
  replaceBrokenImage,
  sanitizeInput,
  toggleMetadataMessages,
} from "@/lib/messages";
import type { ChatConfig, ChatCookies, ChatMessage, ClientContext, SmarterChatProps } from "@/types";
import AppTitle from "@/components/AppTitle";
import ErrorBoundary from "@/components/ErrorBoundary";
import { BanterSparkleIcon, NewChatIcon, ProductionIcon, SandboxIcon } from "@/components/SmarterChat/icons";
import "@/components/SmarterChat/styles.css";

/** The css class of a message, by its sender. */
function messageClassName(sender: string): string {
  if (sender === SenderRoleEnum.SMARTER) return "smarter-message";
  if (sender === SenderRoleEnum.SMARTER_ERROR) return "smarter-error-message";
  if (sender === SenderRoleEnum.TOOL || sender === SenderRoleEnum.SYSTEM) return "system-message";
  return "";
}

/** A step of the running prompt, as a chat message, which is never sent to the api. */
function progressMessage(event: PromptProgressEvent) {
  return messageFactory(event.message, SenderRoleEnum.SMARTER).message;
}

function SmarterChat({
  apiUrl,
  apiKey = null,
  toggleMetadata = false,
  csrfCookieName = "csrftoken",
  csrftoken = null,
  debugCookieName = "debug",
  debugCookieExpiration = DEFAULT_COOKIE_EXPIRATION,
  debugMode = false,
  sessionCookieName = "session_key",
  sessionCookieExpiration = DEFAULT_COOKIE_EXPIRATION,
  cookiePath = null,
  cookieDomain = "",
  smarterRequestId = "",
  streamProgress = true,
  language = null,
  verbose = false,
  reloadKey,
  headerActions = null,
  onConfig,
  onNewChat,
  onModeChange,
}: SmarterChatProps) {
  // before anything below translates a message. See lib/i18n.tsx.
  const activeLanguage = activateLanguage(language);
  const [config, setConfig] = useState<ChatConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // sandbox mode, which displays the backend's own messages, is where the mode toggle is. Without it,
  // e.g. on a page that embeds the chat, the thread is the conversation, as the LLMClient's users see it.
  const [showMetadata, setShowMetadata] = useState(toggleMetadata);
  const [isTyping, setIsTyping] = useState(false);
  const [progress, setProgress] = useState<PromptProgressEvent[]>([]);
  // the assistant's bubble of idle banter, while a prompt runs. It's never part of the thread, nor sent to the api.
  // See lib/banter.ts.
  const [banter, setBanter] = useState<string | null>(null);
  // the urls of the styles' logo and avatars that failed to load, which are then not displayed.
  const [brokenImages, setBrokenImages] = useState<ReadonlySet<string>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatAppRef = useRef<HTMLDivElement>(null);
  // whether the configuration's diagnostic parts are current: fetched with verbose, and since the last prompt.
  const [configVerbose, setConfigVerbose] = useState(false);
  // the latest configuration request. An earlier one's response, which arrives later, is ignored.
  const configRequest = useRef(0);

  const cookies: ChatCookies = useMemo(
    () => ({
      // Django's CSRF cookie. Read, never set.
      csrfCookie: cookieMetaFactory(csrfCookieName, null, cookieDomain, csrftoken),
      // the chat session's key, per page path (or cookiePath), so that each LLMClient has its own chat session.
      sessionCookie: cookieMetaFactory(sessionCookieName, sessionCookieExpiration, cookieDomain, null, cookiePath),
      debugCookie: cookieMetaFactory(debugCookieName, debugCookieExpiration, cookieDomain, null, cookiePath),
    }),
    [
      csrfCookieName,
      csrftoken,
      cookieDomain,
      sessionCookieName,
      sessionCookieExpiration,
      cookiePath,
      debugCookieName,
      debugCookieExpiration,
    ],
  );
  const context: ClientContext = useMemo(
    () => ({ smarterClient: projectName, smarterClientVersion: projectVersion, smarterRequestId, apiKey }),
    [smarterRequestId, apiKey],
  );
  const debug = useCallback(
    (...args: unknown[]) => {
      if (debugMode || config?.debug_mode) console.log(loggerPrefix, ...args);
    },
    [debugMode, config?.debug_mode],
  );

  /** (Re)loads the configuration, which includes the chat session's history, and, with verbose, its diagnostic parts. */
  const refreshConfig = useCallback(async () => {
    const request = ++configRequest.current;
    const newConfig = await fetchConfig(apiUrl, cookies, context, verbose);
    if (request === configRequest.current) {
      setConfig(newConfig);
      setConfigVerbose(verbose);
    }
    return newConfig;
  }, [apiUrl, cookies, context, verbose]);

  useEffect(() => {
    // the page asks for the configuration's diagnostic parts: fetch them, unless they're current.
    if (!verbose || !config || configVerbose) return;
    refreshConfig().catch((error) => console.error(`${loggerPrefix} Failed to refresh:`, error));
  }, [verbose, config, configVerbose, refreshConfig]);

  // the page asks for the configuration again, e.g. after it changed the LLMClient's manifest.
  const previousReloadKey = useRef(reloadKey);
  useEffect(() => {
    if (reloadKey === previousReloadKey.current) return;
    previousReloadKey.current = reloadKey;
    refreshConfig().catch((error) => console.error(`${loggerPrefix} Failed to refresh:`, error));
  }, [reloadKey, refreshConfig]);

  // the page follows the configuration, and the mode.
  useEffect(() => {
    if (config) onConfig?.(config);
  }, [config, onConfig]);
  useEffect(() => {
    onModeChange?.(showMetadata);
  }, [showMetadata, onModeChange]);

  /** Starts, or restores, the chat session. */
  const startChat = useCallback(async () => {
    try {
      setConfigError(null);
      const newConfig = await refreshConfig();
      const llmclient = newConfig.llmclient;
      const thread = chatInit(
        llmclient.app_welcome_message ?? "",
        llmclient.default_system_role ?? "",
        llmclient.app_example_prompts,
        newConfig.history?.chat_history,
      );
      setMessages(toggleMetadataMessages(thread, toggleMetadata, MetadataRolesEnum));
      setShowMetadata(toggleMetadata);
      setIsTyping(false);
      debug("chat started", newConfig);
    } catch (error) {
      console.error(`${loggerPrefix} Failed to fetch the configuration:`, error);
      setConfigError(error instanceof Error ? error.message : String(error));
    }
  }, [refreshConfig, debug, toggleMetadata]);

  useEffect(() => {
    // the first render. startChat() sets state only once the configuration arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void startChat();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl]);

  useEffect(() => {
    // @chatscope's message input is a contenteditable div, without a role or a name.
    const editor = chatAppRef.current?.querySelector(".cs-message-input__content-editor");
    editor?.setAttribute("role", "textbox");
    editor?.setAttribute("aria-multiline", "true");
    editor?.setAttribute("aria-label", gettext("Message"));
  }, [activeLanguage]);

  useEffect(() => {
    // messages are html strings, so their code blocks' copy buttons, and their diagrams' code
    // buttons, are handled here. See lib/code.ts and lib/mermaid.ts.
    const chatApp = chatAppRef.current;
    const handleClick = (event: MouseEvent) => copyCodeBlock(event.target) || toggleMermaidDiagram(event.target);
    chatApp?.addEventListener("click", handleClick);
    return () => chatApp?.removeEventListener("click", handleClick);
  }, []);

  useEffect(() => {
    // a logo or avatar whose image fails to load is hidden, rather than displayed as a broken image,
    // and a message's image is replaced with its description. Errors don't bubble, so they're
    // listened to as they are captured.
    const chatApp = chatAppRef.current;
    const handleError = (event: Event) => {
      if (replaceBrokenImage(event.target)) return;
      const image = event.target;
      if (!(image instanceof HTMLImageElement) || !image.closest(".cs-avatar")) return;
      const src = image.getAttribute("src") ?? "";
      setBrokenImages((previous) => (previous.has(src) ? previous : new Set(previous).add(src)));
    };
    chatApp?.addEventListener("error", handleError, true);
    return () => chatApp?.removeEventListener("error", handleError, true);
  }, []);

  useLayoutEffect(() => {
    // mermaid code blocks are displayed as diagrams once they are in the page. A diagram that was
    // displayed before is cached, and replaces its code before the browser paints. See lib/mermaid.ts.
    void renderMermaidDiagrams(chatAppRef.current);
  }, [messages, showMetadata]);

  const handleNewChat = () => {
    setCookie(cookies.sessionCookie, "");
    setConfig(null);
    onNewChat?.();
    void startChat();
  };

  // while a prompt runs, its first line of banter after BANTER_DELAY_MS, then a new one every BANTER_INTERVAL_MS,
  // whatever its progress events. sendMessage() removes the bubble when the prompt finishes.
  useEffect(() => {
    if (!isTyping) return undefined;
    let interval: ReturnType<typeof setInterval> | undefined;
    const delay = setTimeout(() => {
      setBanter(idleBanter());
      interval = setInterval(() => setBanter(idleBanter()), BANTER_INTERVAL_MS);
    }, BANTER_DELAY_MS);
    return () => {
      clearTimeout(delay);
      clearInterval(interval);
    };
  }, [isTyping]);

  /** Switches to sandbox mode (show) or production mode. The current mode's option does nothing. */
  const handleMode = (show: boolean) => {
    if (show === showMetadata) return;
    setShowMetadata(show);
    setMessages((previous) => toggleMetadataMessages(previous, show, MetadataRolesEnum));
  };

  /** Sends the thread, with the user's new message, to the prompt api. */
  async function sendMessage(text: string) {
    if (!config) return;
    const thread = [...messages, messageFactory(text, SenderRoleEnum.USER)];
    setMessages(thread);
    setIsTyping(true);
    setProgress([]);
    const onProgress = streamProgress
      ? (event: PromptProgressEvent) => {
          debug("prompt progress", event);
          setProgress((previous) => [...previous, event]);
        }
      : undefined;
    try {
      const result = await fetchPrompt(config, chatMessages2RequestMessages(thread), cookies, context, onProgress);
      const responseMessages = result.messages.map((message) => {
        const chatMessage = messageFactory(message.content, message.role, message);
        const hidden = MetadataRolesEnum.includes(chatMessage.sender as never) && !showMetadata;
        return hidden ? { ...chatMessage, display: false } : chatMessage;
      });
      setMessages((previous) => [...previous, ...responseMessages]);
      debug("prompt response", result);
      // the prompt changed the session's history: its tool calls, if the page asks for them, or else
      // when it next does.
      if (verbose) {
        await refreshConfig().catch((error) => console.error(`${loggerPrefix} Failed to refresh:`, error));
      } else {
        setConfigVerbose(false);
      }
    } catch (error) {
      console.error(`${loggerPrefix} Prompt failed:`, error);
      const errorText = error instanceof Error ? error.message : String(error);
      setMessages((previous) => [...previous, messageFactory(errorText, SenderRoleEnum.SMARTER_ERROR)]);
    } finally {
      setIsTyping(false);
      setProgress([]);
      setBanter(null);
    }
  }

  // MessageInput passes its html, text content and inner text. The text has no html.
  const handleSend = (innerHtml: string, textContent: string, innerText: string) => {
    const text = innerText ?? textContent ?? sanitizeInput(innerHtml);
    if (!text.trim()) return;
    void sendMessage(text);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    file.text().then((text) => void sendMessage(text));
    event.target.value = "";
  };

  const llmclient = config?.llmclient;
  const isReady = !!config;
  const styles = llmclient?.styles;
  const rootStyle = useMemo(() => styleVariables(styles), [styles]);
  useGoogleFont(styles?.google_font);
  const imageUrl = (url: string | null | undefined) => {
    const safeUrl = safeImageUrl(url);
    return safeUrl && !brokenImages.has(safeUrl) ? safeUrl : null;
  };
  const logoUrl = imageUrl(styles?.app_logo_url);
  const assistantAvatarUrl = imageUrl(styles?.assistant_avatar_url);
  const userAvatarUrl = imageUrl(styles?.user_avatar_url);
  const title = llmclient ? `${llmclient.app_name} v${llmclient.version || "1.0.0"}` : "";
  const totalTools = llmclient?.total_tools ?? 0;
  let info = "";
  if (llmclient && totalTools > 0) {
    info = interpolate(
      // Translators: the LLM provider and model of the chat, e.g. "openai gpt-4o-mini with 3 additional tools".
      ngettext(
        "%(provider)s %(model)s with %(count)s additional tool",
        "%(provider)s %(model)s with %(count)s additional tools",
        totalTools,
      ),
      { provider: llmclient.provider, model: llmclient.default_model, count: totalTools },
    );
  } else if (llmclient) {
    info = `${llmclient.provider} ${llmclient.default_model}`;
  }
  const isValid = config?.meta_data?.is_valid ?? config?.meta_data?.ready ?? true;
  const isDeployed = !!(config?.meta_data?.is_deployed ?? llmclient?.deployed);

  const assistant = llmclient?.app_assistant ?? gettext("Assistant");

  /** The avatar beside a message: the assistant's, or the user's, if the styles have one. */
  function messageAvatar(message: ChatMessage) {
    if (message.sender === SenderRoleEnum.ASSISTANT && assistantAvatarUrl) {
      return <Avatar src={assistantAvatarUrl} name={assistant} />;
    }
    if (message.sender === SenderRoleEnum.USER && userAvatarUrl) {
      return <Avatar src={userAvatarUrl} name={gettext("You")} />;
    }
    return null;
  }
  const currentStep = progress.at(-1)?.message;
  const typingText = currentStep
    ? // Translators: the assistant's name, and the current step of the running prompt, which is in English.
      interpolate(gettext("%(assistant)s: %(step)s"), { assistant, step: currentStep })
    : interpolate(gettext("%(assistant)s is typing"), { assistant });

  let headerName;
  if (configError) {
    headerName = gettext("Smarter Chat is not available");
  } else if (isReady) {
    headerName = <AppTitle title={title} isReady={isReady} isValid={isValid} isDeployed={isDeployed} />;
  } else {
    headerName = gettext("Configuring workbench...");
  }

  return (
    <div id="smarter_chat_component_container" className="SmarterChat" style={rootStyle}>
      <div className="smarter-chat-container">
        <div role="region" aria-label={gettext("Chat")} className="smarter-chat-app">
          <div className="chat-app" ref={chatAppRef}>
            <ErrorBoundary>
              <MainContainer style={{ width: "100%", height: "100%" }}>
                <ChatContainer className="smarter-chat-container-inner">
                  <ConversationHeader>
                    {logoUrl && isReady && (
                      <Avatar className="smarter-chat-logo" src={logoUrl} name={llmclient?.app_name ?? ""} />
                    )}
                    <ConversationHeader.Content userName={headerName} info={isReady ? info : ""} />
                    <ConversationHeader.Actions>
                      {toggleMetadata && (
                        <div role="group" aria-label={gettext("Chat mode")} className="smarter-chat-mode-toggle">
                          <Button
                            className="smarter-chat-toolbar-button smarter-chat-mode-option"
                            icon={<SandboxIcon />}
                            aria-pressed={showMetadata}
                            onClick={() => handleMode(true)}
                            title={gettext(
                              "Sandbox mode: Smarter's system, tool and meta data messages are displayed.",
                            )}
                          >
                            <span className="smarter-chat-toolbar-label">
                              {/* Translators: the sandbox mode option of the chat's mode switch. */}
                              {pgettext("chat mode", "Sandbox")}
                            </span>
                          </Button>
                          <Button
                            className="smarter-chat-toolbar-button smarter-chat-mode-option"
                            icon={<ProductionIcon />}
                            aria-pressed={!showMetadata}
                            onClick={() => handleMode(false)}
                            title={gettext("Production mode: the conversation is displayed as its users see it.")}
                          >
                            <span className="smarter-chat-toolbar-label">
                              {/* Translators: the production mode option of the chat's mode switch. */}
                              {pgettext("chat mode", "Production")}
                            </span>
                          </Button>
                        </div>
                      )}
                      <Button
                        className="smarter-chat-toolbar-button"
                        icon={<NewChatIcon />}
                        onClick={handleNewChat}
                        title={gettext("Start a new chat")}
                        aria-label={gettext("Start a new chat")}
                      />
                      {headerActions}
                    </ConversationHeader.Actions>
                  </ConversationHeader>
                  <MessageList
                    className="smarter-chat-message-list"
                    scrollBehavior="auto"
                    typingIndicator={isTyping ? <TypingIndicator content={typingText} /> : null}
                  >
                    {configError && (
                      <Message
                        className="smarter-error-message"
                        model={{
                          message: messageFactory(configError, SenderRoleEnum.SMARTER_ERROR).message,
                          direction: "incoming",
                          position: "single",
                          sender: SenderRoleEnum.SMARTER_ERROR,
                        }}
                      />
                    )}
                    {messages.map((message, index) =>
                      message.display ? (
                        <Message
                          key={index}
                          className={messageClassName(message.sender)}
                          model={{
                            message: message.message,
                            sentTime: message.sentTime,
                            sender: message.sender,
                            direction: message.direction,
                            position: "single",
                          }}
                        >
                          {messageAvatar(message)}
                        </Message>
                      ) : null,
                    )}
                    {showMetadata &&
                      progress.map((event, index) => (
                        <Message
                          key={`progress-${index}`}
                          className={`smarter-progress-message ${
                            index === progress.length - 1
                              ? "smarter-progress-message-active"
                              : "smarter-progress-message-done"
                          }`}
                          model={{
                            message: progressMessage(event),
                            sender: SenderRoleEnum.SMARTER,
                            direction: "incoming",
                            position: "single",
                          }}
                        />
                      ))}
                    {isTyping && banter && (
                      <Message
                        className="smarter-chat-banter-message"
                        model={{
                          type: "custom",
                          sender: SenderRoleEnum.ASSISTANT,
                          direction: "incoming",
                          position: "single",
                        }}
                      >
                        {assistantAvatarUrl ? <Avatar src={assistantAvatarUrl} name={assistant} /> : null}
                        <Message.CustomContent>
                          <span className="smarter-chat-banter" aria-live="polite">
                            <BanterSparkleIcon />
                            {banter}
                          </span>
                        </Message.CustomContent>
                      </Message>
                    )}
                  </MessageList>
                  <MessageInput
                    placeholder={llmclient?.app_placeholder ?? ""}
                    onSend={handleSend}
                    onAttachClick={() => fileInputRef.current?.click()}
                    attachButton={!!llmclient?.app_file_attachment}
                    disabled={!isReady}
                    fancyScroll={false}
                    // text copied from a chat bubble, e.g. an example prompt, pastes without the bubble's styles.
                    onPaste={pastePlainText}
                  />
                </ChatContainer>
              </MainContainer>
            </ErrorBoundary>
            <input
              type="file"
              accept=".py,.txt,.md,.json,.yaml,.yml,.csv"
              aria-label={gettext("Attach a file")}
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default SmarterChat;
