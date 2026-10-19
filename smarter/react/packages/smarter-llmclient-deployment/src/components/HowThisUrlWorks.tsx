/**
 * "How this url works": the LLMClient's two endpoints, with the curl commands that call them, an
 * abbreviated response, and the LLMClient's example prompts.
 */
import type { ReactNode } from "react";
import { gettext } from "@smarter/common";

import Terminal from "./Terminal";
import type { LLMClientDeploymentPage } from "../lib/types";

/** One of the four things to know about the url. */
function Fact({ icon, title, text }: { icon: string; title: ReactNode; text: string }) {
  return (
    <div className="col-md-6 col-xl-3">
      <div className="d-flex align-items-start">
        <i className={`ki-outline ${icon} fs-2x text-primary me-4`} aria-hidden="true" />
        <div>
          <h3 className="fw-bold text-gray-900 fs-5 mb-1">{title}</h3>
          <div className="text-gray-600 fs-6">{text}</div>
        </div>
      </div>
    </div>
  );
}

export default function HowThisUrlWorks({ page }: { page: LLMClientDeploymentPage }) {
  const { llmclient, snippets, authenticated, mode } = page;
  return (
    <section id="api" className={`${mode === "public" ? "py-15 py-lg-20" : "py-12"} bg-light`}>
      <div className="container-xxl">
        <div className="text-center mb-12">
          <div className="smarter-section-kicker fw-bold fs-7 mb-3">{gettext("Under the hood")}</div>
          <h2 className="fs-2hx fw-bolder text-gray-900 mb-4">{gettext("How this url works")}</h2>
          <p className="fs-5 text-gray-600 mw-750px mx-auto">
            {gettext(
              "Smarter Chat sends this url two kinds of requests, and so can your own code. Both are POST requests, with JSON in and JSON out. Copy a command into a terminal to try it.",
            )}
            {authenticated && (
              <> {gettext("This LLMClient requires a Smarter api key: replace <YOUR-API-KEY> with yours.")}</>
            )}
          </p>
        </div>
        <div className="row g-8 mb-12">
          <Fact
            icon="ki-message-programming"
            title={
              <>
                <code>/config/</code> {gettext("starts a chat")}
              </>
            }
            text={gettext(
              "It returns the LLMClient's configuration, such as its name, welcome message, example prompts and colors, and a session_key for the new chat.",
            )}
          />
          <Fact
            icon="ki-send"
            title={
              <>
                <code>/prompt/</code> {gettext("sends a prompt")}
              </>
            }
            text={gettext(
              "It returns the messages that the prompt added to the chat. Send the session_key with every prompt, and Smarter keeps the chat's history.",
            )}
          />
          <Fact
            icon="ki-code"
            title={gettext("Answers are Markdown")}
            text={gettext(
              "The response is JSON, and the assistant's message in it is Markdown. Smarter Chat renders it, with code highlighting, math and diagrams. In your own front end, use any Markdown library.",
            )}
          />
          <Fact
            icon="ki-lock"
            title={gettext("Secrets stay on the server")}
            text={gettext(
              "Smarter calls the LLM and runs the tools. Their api keys and credentials never reach the browser.",
            )}
          />
        </div>
        <div className="row g-8">
          <div className="col-xl-6">
            <h3 className="fw-bold text-gray-900 mb-2">
              <code className="fs-4">POST /config/</code>
            </h3>
            <p className="text-gray-600 fs-6 mb-5">
              {gettext(
                "The chat's configuration, and a new chat session, whose session_key continues the chat in later prompts.",
              )}
            </p>
            <Terminal title="bash" code={snippets.configCommand} />
          </div>
          <div className="col-xl-6">
            <h3 className="fw-bold text-gray-900 mb-2">
              <code className="fs-4">POST /prompt/</code>
            </h3>
            <p className="text-gray-600 fs-6 mb-5">
              {llmclient.examplePrompts.length
                ? gettext("Sends the LLMClient's first example prompt, and returns the LLM's response.")
                : gettext("Sends a prompt, and returns the LLM's response.")}
            </p>
            <Terminal title="bash" code={snippets.promptCommand} />
            <p className="text-gray-600 fs-6 mt-6 mb-3">{gettext("The response, abbreviated:")}</p>
            <Terminal title="200 OK  application/json" code={snippets.exampleResponse} />
          </div>
        </div>
        {llmclient.examplePrompts.length > 0 && (
          <div className="text-center mt-12">
            <h3 className="text-gray-600 fw-semibold fs-6 mb-4">{gettext("Things to ask it")}</h3>
            <ul className="list-unstyled d-flex flex-wrap justify-content-center gap-3 mb-0">
              {llmclient.examplePrompts.map((example) => (
                <li key={example} className="badge badge-light-primary fs-6 fw-semibold px-4 py-3">
                  {example}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
