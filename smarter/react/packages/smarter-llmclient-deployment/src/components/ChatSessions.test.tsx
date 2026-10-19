import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ChatSessions from "@/components/ChatSessions";
import { publicPage, workbenchPage } from "@/mocks/fixtures";

describe("ChatSessions", () => {
  it("explains what a session key is, who makes it, keeps it, and ends it", () => {
    render(<ChatSessions page={publicPage} />);
    expect(screen.getByRole("heading", { level: 2, name: "Chat sessions" })).toBeInTheDocument();
    expect(screen.getByText(/Every conversation with Stackademy Support Bot is a chat session/)).toBeInTheDocument();
    for (const name of ["The platform makes it", "The client keeps it", "Forgetting it starts over"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: "Smarter Chat does it for you" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Keep a session key private" })).toBeInTheDocument();
  });

  it("walks a front end through a session, with the commands that carry its key", () => {
    render(<ChatSessions page={workbenchPage} />);
    const steps = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(steps.map((step) => within(step).getByRole("heading").textContent)).toEqual([
      "Start a session",
      "Keep the key",
      "Send it with every prompt",
      "Come back to it",
    ]);
    const [prompt, config] = screen.getAllByRole("group", { name: "bash" });
    expect(prompt).toHaveTextContent('"session_key":"<SESSION-KEY>","messages"');
    expect(prompt).toHaveTextContent("/prompt/");
    expect(config).toHaveTextContent('{"session_key":"<SESSION-KEY>"}');
    expect(config).toHaveTextContent("/config/");
  });
});
