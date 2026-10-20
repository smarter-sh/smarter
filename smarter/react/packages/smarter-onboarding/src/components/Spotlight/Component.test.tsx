import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import Spotlight from "@/components/Spotlight/Component";
import { addTarget, removeTargets, stubBox } from "@/mocks/targets";

function renderSpotlight(title?: string) {
  const target = addTarget('<a href="#llmclients">LLM Clients</a>');
  const onDone = vi.fn();
  render(<Spotlight target={target} title={title} text="Start building your AI masterpiece here." onDone={onDone} />);
  return { target, onDone };
}

describe("Spotlight", () => {
  afterEach(removeTargets);

  it("rings the element and shows a note beside it, which doesn't take the focus", () => {
    renderSpotlight();
    expect(screen.getByTestId("smarter-onboarding-ring")).toHaveStyle({ top: "94px", left: "14px" });
    const note = screen.getByRole("dialog", { name: "Start building your AI masterpiece here." });
    expect(note).toHaveAttribute("aria-modal", "false");
    expect(screen.getByRole("button", { name: "Got it" })).not.toHaveFocus();
  });

  it("has a title, when it is given one", () => {
    renderSpotlight("Your LLM Clients");
    expect(screen.getByRole("dialog", { name: "Your LLM Clients" })).toHaveAccessibleDescription(
      "Start building your AI masterpiece here.",
    );
  });

  it("is clicked when the user clicks the element, once", () => {
    const { target, onDone } = renderSpotlight();
    fireEvent.click(target);
    fireEvent.click(target);
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onDone).toHaveBeenCalledWith("clicked");
  });

  it("is dismissed with Got it, or Escape", async () => {
    const user = userEvent.setup();
    const { onDone } = renderSpotlight();
    await user.click(screen.getByRole("button", { name: "Got it" }));
    expect(onDone).toHaveBeenCalledWith("dismissed");

    removeTargets();
    const { onDone: onDoneAgain } = renderSpotlight();
    await user.keyboard("{Escape}");
    expect(onDoneAgain).toHaveBeenCalledWith("dismissed");
  });

  it("waits while the element is off screen", () => {
    const target = addTarget('<a href="#llmclients">LLM Clients</a>');
    stubBox(target, { top: 0, left: 0, width: 0, height: 0 });
    render(<Spotlight target={target} text="Hidden" onDone={() => {}} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
