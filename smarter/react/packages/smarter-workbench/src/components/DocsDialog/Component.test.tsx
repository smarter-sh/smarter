import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import DocsDialog from "@/components/DocsDialog/Component";
import { docSections } from "@/components/DocsDialog/data";

describe("DocsDialog", () => {
  it("has a tab for each audience, Prompt Engineer first and selected", () => {
    render(<DocsDialog onClose={() => {}} />);
    expect(screen.getByRole("dialog", { name: "Docs" })).toBeInTheDocument();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Prompt Engineer", "Software Engineer"]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tabpanel", { name: "Prompt Engineer" })).toBeInTheDocument();
  });

  it("lists the selected tab's technical references, which open in a new tab", async () => {
    const user = userEvent.setup();
    render(<DocsDialog onClose={() => {}} />);
    for (const section of docSections()) {
      await user.click(screen.getByRole("tab", { name: section.title }));
      const panel = screen.getByRole("tabpanel", { name: section.title });
      expect(within(panel).getAllByRole("link")).toHaveLength(section.links.length);
      for (const link of section.links) {
        const anchor = within(panel).getByRole("link", { name: link.title });
        expect(anchor).toHaveAttribute("href", link.url);
        expect(anchor).toHaveAttribute("target", "_blank");
        expect(anchor).toHaveAttribute("rel", "noopener noreferrer");
      }
    }
  });

  it("moves between its tabs with the arrow, Home and End keys", async () => {
    const user = userEvent.setup();
    render(<DocsDialog onClose={() => {}} />);
    const [prompt, software] = screen.getAllByRole("tab");
    await user.click(prompt);

    await user.keyboard("{ArrowRight}");
    expect(software).toHaveFocus();
    expect(software).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{ArrowRight}");
    expect(prompt).toHaveFocus();

    await user.keyboard("{ArrowLeft}");
    expect(software).toHaveFocus();

    await user.keyboard("{Home}");
    expect(prompt).toHaveFocus();

    await user.keyboard("{End}");
    expect(software).toHaveFocus();

    await user.keyboard("a");
    expect(software).toHaveFocus();
    expect(prompt).toHaveAttribute("tabindex", "-1");
    expect(software).toHaveAttribute("tabindex", "0");
  });

  it("focuses its close button", () => {
    render(<DocsDialog onClose={() => {}} />);
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();
  });

  it("closes with its close button, with Escape, and with a click outside of it", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<DocsDialog onClose={onClose} />);

    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);

    await user.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(2);

    await user.click(document.body);
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("displays other tabs", () => {
    render(
      <DocsDialog
        onClose={() => {}}
        sections={[
          {
            title: "Examples",
            description: "",
            links: [{ title: "Example", url: "https://example.com/", description: "" }],
          },
        ]}
      />,
    );
    expect(screen.getByRole("tab", { name: "Examples" })).toHaveAttribute("aria-selected", "true");
    const panel = screen.getByRole("tabpanel", { name: "Examples" });
    expect(within(panel).getByRole("link", { name: "Example" })).toHaveAttribute("href", "https://example.com/");
  });
});
