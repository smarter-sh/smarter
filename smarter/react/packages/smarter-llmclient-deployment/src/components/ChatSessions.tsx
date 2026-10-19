/**
 * "Chat sessions": how a conversation with the LLMClient lasts across page loads. The platform generates a
 * session key, the client keeps it and sends it with each request, and the platform keeps the session's messages.
 * What Smarter Chat does with it, and what a developer's own front end does, with the curl commands.
 */
import type { ReactNode } from "react";
import { gettext, interpolate, interpolateNodes } from "@smarter/common";

import Terminal from "./Terminal";
import type { LLMClientDeploymentPage } from "../lib/types";

/** One of the three things to know about a session key. */
function Fact({ icon, title, children }: { icon: string; title: string; children: ReactNode }) {
  return (
    <div className="col-md-4">
      <div className="d-flex align-items-start">
        <i className={`ki-outline ${icon} fs-2x text-primary me-4`} aria-hidden="true" />
        <div>
          <h3 className="fw-bold text-gray-900 fs-5 mb-1">{title}</h3>
          <div className="text-gray-600 fs-6">{children}</div>
        </div>
      </div>
    </div>
  );
}

/** A numbered step of a front end's sessions, with its command, if it has one. */
function Step({ step, title, children }: { step: number; title: string; children: ReactNode }) {
  return (
    <li className="mb-8">
      <div className="d-flex align-items-center mb-3">
        <span className="smarter-step me-3" aria-hidden="true">
          {step}
        </span>
        <h4 className="fw-bold text-gray-900 fs-5 mb-0">{title}</h4>
      </div>
      {children}
    </li>
  );
}

export default function ChatSessions({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, snippets, mode } = page;
  const code = (text: string) => <code>{text}</code>;
  return (
    <section id="sessions" className={`${mode === "public" ? "py-15 py-lg-20" : "py-12"} border-top`}>
      <div className="container-xxl">
        <div className="text-center mb-12">
          <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("Conversations")}</div>
          <h2 className="fs-2hx fw-bolder text-gray-900 mb-4">{gettext("Chat sessions")}</h2>
          <p className="fs-5 text-gray-600 mw-750px mx-auto">
            {interpolate(
              gettext(
                "Every conversation with %(app_name)s is a chat session, which the platform identifies by a session key. The session's messages are stored on the platform, so a conversation survives a page reload, or a visit to another page: the chat sends its key, and the platform answers with the conversation so far.",
              ),
              { app_name: llmclient.appName },
            )}
          </p>
        </div>

        <div className="row g-8 mb-12">
          <Fact icon="ki-key" title={gettext("The platform makes it")}>
            {interpolateNodes(
              gettext(
                "The first %(config)s request of a chat that has no key gets a new one, 64 hexadecimal characters, in the response's %(field)s. Don't make up your own: the platform checks its format.",
              ),
              { config: code("/config/"), field: code("data.session_key") },
            )}
          </Fact>
          <Fact icon="ki-save-2" title={gettext("The client keeps it")}>
            {gettext(
              "The key is all that the client stores: the browser, or your own server. The session's messages, and the platform's records of its tool calls and costs, stay on the platform.",
            )}
          </Fact>
          <Fact icon="ki-arrows-circle" title={gettext("Forgetting it starts over")}>
            {interpolateNodes(
              gettext(
                "A %(config)s request without a key starts a new session, with a new key. That is all that Smarter Chat's New chat button does.",
              ),
              { config: code("/config/") },
            )}
          </Fact>
        </div>

        <div className="row g-10">
          <div className="col-xl-5">
            <h3 className="fw-bold text-gray-900 mb-4">{gettext("Smarter Chat does it for you")}</h3>
            <p className="text-gray-600 fs-6 mb-4">
              {interpolateNodes(
                gettext(
                  "Smarter Chat keeps the key in a cookie, %(cookie)s by default, for one day, and for the page's path, so that each page has its own conversation. Set %(cookie_path)s to %(root)s to keep one conversation as the visitor moves from page to page. The embed script keeps its own cookie, for the whole site.",
                ),
                { cookie: code("session_key"), cookie_path: code("cookiePath"), root: code('"/"') },
              )}
            </p>
            <p className="text-gray-600 fs-6 mb-0">
              {gettext(
                "The WordPress, Drupal and Shopify integrations, and the html snippet, use Smarter Chat, so they need nothing more.",
              )}
            </p>
          </div>
          <div className="col-xl-7">
            <h3 className="fw-bold text-gray-900 mb-4">{gettext("In your own front end")}</h3>
            <ol className="list-unstyled mb-0">
              <Step step={1} title={gettext("Start a session")}>
                <p className="text-gray-600 fs-6 mb-0">
                  {interpolateNodes(
                    gettext(
                      "Send %(config)s with no key, as the first command in How this url works does. Its response's %(field)s is the new session's key.",
                    ),
                    { config: code("POST /config/"), field: code("data.session_key") },
                  )}
                </p>
              </Step>
              <Step step={2} title={gettext("Keep the key")}>
                <p className="text-gray-600 fs-6 mb-0">
                  {gettext(
                    "In the browser, in localStorage or a cookie. In a server-to-server integration, in your own database, beside your user, so that each of your users has their own conversation.",
                  )}
                </p>
              </Step>
              <Step step={3} title={gettext("Send it with every prompt")}>
                <p className="text-gray-600 fs-6 mb-4">
                  {interpolateNodes(
                    gettext(
                      "Add it to the body, as %(field)s. The request still carries the whole conversation, in %(messages)s, and the platform adds the new messages to the session.",
                    ),
                    { field: code("session_key"), messages: code("messages") },
                  )}
                </p>
                <Terminal title="bash" code={snippets.sessionPromptCommand} />
              </Step>
              <Step step={4} title={gettext("Come back to it")}>
                <p className="text-gray-600 fs-6 mb-4">
                  {interpolateNodes(
                    gettext(
                      "After a reload, send %(config)s with the key. Its response's %(history)s is the conversation so far, to display again, and its %(field)s is the same key.",
                    ),
                    {
                      config: code("POST /config/"),
                      history: code("data.history.chat_history"),
                      field: code("data.session_key"),
                    },
                  )}
                </p>
                <Terminal title="bash" code={snippets.sessionConfigCommand} />
              </Step>
            </ol>
          </div>
        </div>

        <div className="notice d-flex bg-light-warning rounded border-warning border border-dashed p-6 mt-4">
          <i className="ki-outline ki-shield-cross fs-2tx text-warning me-4" aria-hidden="true" />
          <div className="flex-grow-1 min-w-0 fs-6 text-gray-700">
            <h3 className="text-gray-900 fw-bold fs-4 mb-2">{gettext("Keep a session key private")}</h3>
            <p className="mb-0">
              {interpolateNodes(
                gettext(
                  "Anyone who has a session key, and can call this url, can read its conversation, with the %(config)s request above. Don't put it in a url that people share, in a log, or in an analytics event. It doesn't authenticate the caller: an api key does that.",
                ),
                { config: code("/config/") },
              )}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
