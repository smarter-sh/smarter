import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { appContext, welcome } from "@/mocks/fixtures";
import type { WelcomeUrls } from "@/lib/Types";

import WelcomeDialog from "@/components/WelcomeDialog/Component";

function renderDialog({
  firstName = "Ada",
  urls = welcome.urls,
  error = null,
  showAtStartup = true,
}: { firstName?: string; urls?: WelcomeUrls | null; error?: string | null; showAtStartup?: boolean } = {}) {
  const onShowAtStartupChange = vi.fn();
  const onLastStep = vi.fn();
  const onClose = vi.fn();
  render(
    <WelcomeDialog
      firstName={firstName}
      logoUrl={appContext.logoUrl}
      illustrationsUrl={appContext.illustrationsUrl}
      urls={urls}
      error={error}
      showAtStartup={showAtStartup}
      onShowAtStartupChange={onShowAtStartupChange}
      onLastStep={onLastStep}
      onClose={onClose}
    />,
  );
  return { onShowAtStartupChange, onLastStep, onClose };
}

describe("WelcomeDialog", () => {
  it("greets the user by name, in a modal dialog", () => {
    renderDialog();
    const dialog = screen.getByRole("dialog", { name: "Welcome to Smarter, Ada!" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleDescription(/sophisticated AI solutions/);
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();
    expect(screen.getByRole("button", { name: "Go to step 1" })).toHaveAttribute("aria-current", "step");
  });

  it("greets a user without a first name", () => {
    renderDialog({ firstName: "" });
    expect(screen.getByRole("dialog", { name: "Welcome to Smarter!" })).toBeInTheDocument();
  });

  it("shows each step's illustration, for the light and the dark theme", () => {
    renderDialog();
    // the illustrations are decorative: hidden from assistive technology, with an empty alt.
    const sources = screen.getAllByRole("presentation", { hidden: true }).map((img) => img.getAttribute("src"));
    expect(sources).toEqual([`${appContext.illustrationsUrl}1.png`, `${appContext.illustrationsUrl}1-dark.png`]);
  });

  it("moves between the steps with Next and Back, and calls onLastStep at the last one", async () => {
    const user = userEvent.setup();
    const { onLastStep, onClose } = renderDialog();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Your account is ready to explore" })).toBeInTheDocument();
    expect(screen.getByText("Step 2 of 8")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Welcome to Smarter, Ada!" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Get hands-on with the real thing" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Connect MCP Servers" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Answer from your own documents" })).toBeInTheDocument();
    expect(screen.getByText("Real databases, real costs")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Host open models yourself" })).toBeInTheDocument();
    expect(screen.getByText("Real servers, real costs")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Built for production, at scale" })).toBeInTheDocument();
    expect(screen.getByText("State-of-the-art orchestration")).toBeInTheDocument();
    expect(onLastStep).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Where to start" })).toBeInTheDocument();
    expect(onLastStep).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Get started" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("moves between the steps with the arrow keys and the dots, and not past either end", async () => {
    const user = userEvent.setup();
    renderDialog();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("heading", { name: "Welcome to Smarter, Ada!" })).toBeInTheDocument();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByText("Step 2 of 8")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByText("Step 8 of 8")).toBeInTheDocument();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByText("Step 7 of 8")).toBeInTheDocument();
  });

  it("has a Show at startup box on its first step only", async () => {
    const user = userEvent.setup();
    const { onShowAtStartupChange } = renderDialog();
    const box = screen.getByRole("checkbox", { name: "Show at startup" });
    expect(box).toBeChecked();
    await user.click(box);
    expect(onShowAtStartupChange).toHaveBeenCalledWith(false);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("leaves the Show at startup box unticked for a user who unticked it", async () => {
    const user = userEvent.setup();
    const { onShowAtStartupChange } = renderDialog({ showAtStartup: false });
    const box = screen.getByRole("checkbox", { name: "Show at startup" });
    expect(box).not.toBeChecked();
    await user.click(box);
    expect(onShowAtStartupChange).toHaveBeenCalledWith(true);
  });

  it("links to where to start, opening the external sites in a new tab", async () => {
    const user = userEvent.setup();
    renderDialog();
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(screen.getByRole("link", { name: /Try the Get Weather LLMClient/ })).toHaveAttribute(
      "href",
      welcome.urls.weather,
    );
    expect(screen.getByRole("link", { name: /Explore your LLMClients/ })).not.toHaveAttribute("target");
    const docs = screen.getByRole("link", { name: /Read the documentation/ });
    expect(docs).toHaveAttribute("href", welcome.urls.docs);
    expect(docs).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: /Visit the Smarter project/ })).toHaveAttribute(
      "href",
      welcome.urls.project,
    );
    expect(screen.getByText("You can take this tour again at any time from the user menu.")).toBeInTheDocument();
  });

  it("leaves out the Get Weather LLMClient when the user can't read one", async () => {
    const user = userEvent.setup();
    renderDialog({ urls: { ...welcome.urls, weather: null } });
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(screen.queryByRole("link", { name: /Get Weather/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(3);
  });

  it("says so while the links load", async () => {
    const user = userEvent.setup();
    renderDialog({ urls: null });
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
  });

  it("shows why the links failed to load", async () => {
    const user = userEvent.setup();
    renderDialog({ urls: null, error: "Request failed: 503" });
    await user.click(screen.getByRole("button", { name: "Go to step 8" }));
    expect(screen.getByText("Failed to load the links: Request failed: 503")).toBeInTheDocument();
  });

  it("closes with Escape, the close button, Skip tour and the backdrop, but not a click inside it", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDialog();
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.click(screen.getByRole("button", { name: "Skip tour" }));
    await user.click(screen.getByRole("heading", { name: "Welcome to Smarter, Ada!" }));
    expect(onClose).toHaveBeenCalledTimes(3);
    // the backdrop has no role: a click on it is a mouse convenience, whose keyboard equivalent is Escape.
    // eslint-disable-next-line testing-library/no-node-access
    await user.click(screen.getByRole("dialog").parentElement as HTMLElement);
    expect(onClose).toHaveBeenCalledTimes(4);
  });

  it("keeps the focus inside the dialog", async () => {
    const user = userEvent.setup();
    renderDialog();
    const close = screen.getByRole("button", { name: "Close" });
    const next = screen.getByRole("button", { name: "Next" });
    expect(next).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.tab({ shift: true });
    expect(next).toHaveFocus();
  });

  it("keeps the page behind it from scrolling while it's open", () => {
    document.body.style.overflow = "auto";
    const { unmount } = render(
      <WelcomeDialog
        firstName=""
        logoUrl=""
        illustrationsUrl=""
        urls={null}
        error={null}
        showAtStartup={true}
        onShowAtStartupChange={() => {}}
        onLastStep={() => {}}
        onClose={() => {}}
      />,
    );
    expect(document.body).toHaveStyle({ overflow: "hidden" });
    unmount();
    expect(document.body).toHaveStyle({ overflow: "auto" });
  });
});
