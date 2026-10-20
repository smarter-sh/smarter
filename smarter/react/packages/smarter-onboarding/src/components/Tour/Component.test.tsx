import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Tour, { type TourStep } from "@/components/Tour/Component";
import { addTarget, removeTargets } from "@/mocks/targets";

const steps: TourStep[] = [
  { title: "Welcome to the workbench", text: "A short tour." },
  { target: "#chat", title: "The chat", text: "Talk to the LLMClient here." },
  { target: "#missing", title: "A tab this LLMClient lacks", text: "Left out." },
  { target: "#console", title: "The Console", text: "How it works." },
];

describe("Tour", () => {
  beforeEach(() => {
    addTarget('<div id="chat">Chat</div>', { top: 0, left: 0, width: 600, height: 700 });
    addTarget('<div id="console">Console</div>', { top: 0, left: 620, width: 500, height: 700 });
  });
  afterEach(removeTargets);

  it("goes through the steps whose element is on the page, and completes", async () => {
    const user = userEvent.setup();
    const onFinish = vi.fn();
    render(<Tour steps={steps} onFinish={onFinish} />);
    const dialog = screen.getByRole("dialog", { name: "Welcome to the workbench" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleDescription("A short tour.");
    expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();
    expect(screen.queryByTestId("smarter-onboarding-ring")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog", { name: "The chat" })).toBeInTheDocument();
    expect(screen.getByTestId("smarter-onboarding-ring")).toHaveStyle({ top: "-8px", left: "-8px" });
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(screen.getByRole("dialog", { name: "The Console" })).toBeInTheDocument();
    expect(screen.getByText("Step 3 of 3")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}{ArrowLeft}");
    expect(screen.getByText("Step 2 of 3")).toBeInTheDocument();
    await user.keyboard("{ArrowRight}");
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(onFinish).toHaveBeenCalledExactlyOnceWith("completed");
  });

  it("is dismissed with Skip tour or Escape", async () => {
    const user = userEvent.setup();
    const onFinish = vi.fn();
    const { unmount } = render(<Tour steps={steps} onFinish={onFinish} />);
    await user.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(onFinish).toHaveBeenCalledWith("dismissed");
    unmount();

    const second = vi.fn();
    render(<Tour steps={steps} onFinish={second} />);
    await user.keyboard("{Escape}");
    await user.keyboard("{Escape}");
    expect(second).toHaveBeenCalledExactlyOnceWith("dismissed");
  });

  it("keeps the focus inside the note", async () => {
    const user = userEvent.setup();
    render(<Tour steps={steps} onFinish={() => {}} />);
    const skip = screen.getByRole("button", { name: "Skip tour" });
    const next = screen.getByRole("button", { name: "Next" });
    await user.tab();
    expect(skip).toHaveFocus();
    await user.tab({ shift: true });
    expect(next).toHaveFocus();
  });

  it("clicks the element of a step that activates it, e.g. a tab, when the step shows", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const tab = addTarget('<button type="button" id="tab">Manifest</button>', {
      top: 10,
      left: 700,
      width: 80,
      height: 30,
    });
    tab.addEventListener("click", onClick);
    render(
      <Tour
        steps={[
          steps[0],
          { target: "#chat", title: "The chat", text: "Not clicked." },
          { target: "#tab", activate: true, title: "The manifest", text: "Clicked." },
        ]}
        onFinish={() => {}}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(onClick).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("dialog", { name: "The manifest" })).toBeInTheDocument();
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("completes at once when none of its steps' elements is on the page", () => {
    const onFinish = vi.fn();
    render(<Tour steps={[steps[2]]} onFinish={onFinish} />);
    expect(onFinish).toHaveBeenCalledExactlyOnceWith("completed");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
