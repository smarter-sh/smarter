/**
 * The welcome dialog: a few steps that welcome a new user, and tour what Smarter is, what their
 * account holds, what it teaches, and where to start.
 *
 * It is a modal. Escape, the close button, Skip tour and a click on the backdrop close it. Next and
 * Back, the step dots, and the left and right arrow keys move between the steps, and Tab keeps the
 * focus inside it. The last step links to the Get Weather example LLMClient, the LLMClients, the
 * documentation and the project's website, and its Get started button closes it. The first step has a
 * Show at startup box, whose choice the app records when the dialog closes.
 *
 * :param firstName: The user's first name, which the first step greets, or an empty string.
 * :param logoUrl: The Smarter logo.
 * :param illustrationsUrl: The folder of the Keen dozzy-1 illustrations, ending in a slash.
 * :param urls: The last step's links, or null while they load.
 * :param error: Why the links failed to load, or null.
 * :param showAtStartup: Whether the Show at startup box is ticked.
 * :param onShowAtStartupChange: Called when the user ticks or unticks it.
 * :param onLastStep: Called when the last step shows.
 * :param onClose: Called when the user closes the dialog.
 */
import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { gettext, interpolate, interpolateNodes } from "@smarter/common";

import { welcomeSteps } from "@/components/WelcomeDialog/steps";
import type { WelcomeUrls } from "@/lib/Types";
import "@/components/WelcomeDialog/styles.css";

interface WelcomeDialogProps {
  firstName: string;
  logoUrl: string;
  illustrationsUrl: string;
  urls: WelcomeUrls | null;
  error: string | null;
  showAtStartup: boolean;
  onShowAtStartupChange: (showAtStartup: boolean) => void;
  onLastStep: () => void;
  onClose: () => void;
}

interface WelcomeLink {
  icon: string;
  title: string;
  description: string;
  url: string;
  external: boolean;
}

/** The last step's links. The Get Weather LLMClient's is left out when the user can't read one. */
function welcomeLinks(urls: WelcomeUrls): WelcomeLink[] {
  const links: WelcomeLink[] = [];
  if (urls.weather) {
    links.push({
      icon: "ki-rocket",
      title: gettext("Try the Get Weather LLMClient"),
      description: gettext("Chat with an example that calls a tool to look up the weather."),
      url: urls.weather,
      external: false,
    });
  }
  links.push(
    {
      icon: "ki-message-programming",
      title: gettext("Explore your LLMClients"),
      description: gettext("Chatbots, agents and harnesses, ready to run and customize."),
      url: urls.llmclients,
      external: false,
    },
    {
      icon: "ki-book-open",
      title: gettext("Read the documentation"),
      description: gettext("Guides, manifests, the command-line interface and the API, at docs.smarter.sh."),
      url: urls.docs,
      external: true,
    },
    {
      icon: "ki-github",
      title: gettext("Visit the Smarter project"),
      description: gettext("The open source project, its source code and its community, at smarter.sh."),
      url: urls.project,
      external: true,
    },
  );
  return links;
}

const FOCUSABLE = "a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex='-1'])";

function WelcomeDialog({
  firstName,
  logoUrl,
  illustrationsUrl,
  urls,
  error,
  showAtStartup,
  onShowAtStartupChange,
  onLastStep,
  onClose,
}: WelcomeDialogProps) {
  const steps = welcomeSteps(firstName);
  const last = steps.length - 1;
  const [index, setIndex] = useState(0);
  const step = steps[index];
  const titleId = useId();
  const leadId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);

  // the focus moves onto the primary button of each step, so that Enter goes on, as in a wizard.
  useEffect(() => {
    primaryRef.current?.focus();
  }, [index]);

  useEffect(() => {
    if (index === last) onLastStep();
  }, [index, last, onLastStep]);

  useEffect(() => {
    // the page behind the modal doesn't scroll while it's open.
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
    };
  }, []);

  const goTo = (next: number) => setIndex(Math.max(0, Math.min(last, next)));

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      goTo(index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      goTo(index - 1);
    } else if (event.key === "Tab") {
      // keep the focus inside the dialog.
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const end = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        end.focus();
      } else if (!event.shiftKey && document.activeElement === end) {
        event.preventDefault();
        first.focus();
      }
    }
  };

  return (
    // Clicking the backdrop closes the dialog: a mouse convenience, whose keyboard equivalent is Escape.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <div
      className="smarter-welcome-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- the dialog handles its own keys: Escape, the arrows and Tab. */}
      <div
        ref={dialogRef}
        className="smarter-welcome-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={leadId}
        onKeyDown={handleKeyDown}
      >
        <button
          type="button"
          className="smarter-welcome-close btn btn-icon btn-sm btn-active-light"
          onClick={onClose}
          aria-label={gettext("Close")}
          title={gettext("Close")}
        >
          <i className="ki-outline ki-cross fs-1"></i>
        </button>

        <div className="smarter-welcome-art" aria-hidden="true">
          <img
            key={`light-${step.illustration}`}
            className="smarter-welcome-illustration theme-light-show"
            src={`${illustrationsUrl}${step.illustration}.png`}
            alt=""
          />
          <img
            key={`dark-${step.illustration}`}
            className="smarter-welcome-illustration theme-dark-show"
            src={`${illustrationsUrl}${step.illustration}-dark.png`}
            alt=""
          />
        </div>

        <div className="smarter-welcome-body">
          <div key={index} className="smarter-welcome-step">
            {index === 0 && logoUrl ? (
              <img className="smarter-welcome-logo" src={logoUrl} alt="Smarter" />
            ) : (
              <div className="smarter-welcome-eyebrow">
                {interpolate(gettext("Step %(step)s of %(steps)s"), { step: index + 1, steps: steps.length })}
              </div>
            )}
            <h2 id={titleId} className="smarter-welcome-title">
              {step.title}
            </h2>
            <p id={leadId} className="smarter-welcome-lead">
              {step.lead}
            </p>

            {step.highlights.length > 0 && (
              <ul className="smarter-welcome-highlights">
                {step.highlights.map((highlight) => (
                  <li key={highlight.title}>
                    <span className="smarter-welcome-icon">
                      <i className={`ki-outline ${highlight.icon} fs-2`}></i>
                    </span>
                    <span>
                      <span className="smarter-welcome-highlight-title">{highlight.title}</span>
                      <span className="smarter-welcome-highlight-description">{highlight.description}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {index === last && (
              <>
                {error ? (
                  <p className="text-danger fs-7">
                    {interpolateNodes(gettext("Failed to load the links: %(error)s"), { error })}
                  </p>
                ) : !urls ? (
                  <p className="text-muted fs-7" role="status">
                    {gettext("Loading…")}
                  </p>
                ) : (
                  <ul className="smarter-welcome-links">
                    {welcomeLinks(urls).map((link) => (
                      <li key={link.title}>
                        <a
                          href={link.url}
                          className="smarter-welcome-link"
                          {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                        >
                          <span className="smarter-welcome-icon">
                            <i className={`ki-outline ${link.icon} fs-2`}></i>
                          </span>
                          <span>
                            <span className="smarter-welcome-highlight-title">
                              {link.title}
                              {link.external && (
                                <i className="ki-outline ki-exit-right-corner fs-7 ms-1" aria-hidden="true"></i>
                              )}
                            </span>
                            <span className="smarter-welcome-highlight-description">{link.description}</span>
                          </span>
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="smarter-welcome-reopen">
                  {gettext("You can take this tour again at any time from the user menu.")}
                </p>
              </>
            )}
          </div>

          <div className="smarter-welcome-footer">
            <div className="smarter-welcome-dots">
              {steps.map((dot, dotIndex) => (
                <button
                  key={dot.title}
                  type="button"
                  className={`smarter-welcome-dot ${dotIndex === index ? "active" : ""}`}
                  aria-label={interpolate(gettext("Go to step %(step)s"), { step: dotIndex + 1 })}
                  aria-current={dotIndex === index ? "step" : undefined}
                  onClick={() => goTo(dotIndex)}
                ></button>
              ))}
            </div>
            <div className="smarter-welcome-actions">
              {index === 0 && (
                <label className="form-check form-check-sm form-check-custom form-check-solid smarter-welcome-startup">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    checked={showAtStartup}
                    onChange={(event) => onShowAtStartupChange(event.target.checked)}
                  />
                  <span className="form-check-label">{gettext("Show at startup")}</span>
                </label>
              )}
              {index === 0 ? (
                <button type="button" className="btn btn-sm btn-link text-muted" onClick={onClose}>
                  {gettext("Skip tour")}
                </button>
              ) : (
                <button type="button" className="btn btn-sm btn-light" onClick={() => goTo(index - 1)}>
                  {gettext("Back")}
                </button>
              )}
              {index < last ? (
                <button
                  ref={primaryRef}
                  type="button"
                  className="btn btn-sm smarter-welcome-primary"
                  onClick={() => goTo(index + 1)}
                >
                  {gettext("Next")}
                </button>
              ) : (
                <button ref={primaryRef} type="button" className="btn btn-sm smarter-welcome-primary" onClick={onClose}>
                  {gettext("Get started")}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WelcomeDialog;
