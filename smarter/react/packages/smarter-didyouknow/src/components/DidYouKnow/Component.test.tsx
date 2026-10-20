import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DidYouKnow from "@/components/DidYouKnow/Component";

const withLink = {
  text: "Smarter has an MCP server.",
  link: { label: "Read about it", url: "https://docs.smarter.sh/en/latest/" },
};

describe("DidYouKnow", () => {
  it("shows its title, the fact, and its link, which opens in a new tab", () => {
    render(<DidYouKnow fact={withLink} />);
    const note = screen.getByRole("complementary", { name: "Did you know?" });
    expect(note).toHaveTextContent("Did you know? Smarter has an MCP server. Read about it");
    const link = within(note).getByRole("link", { name: "Read about it" });
    expect(link).toHaveAttribute("href", withLink.link.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows the fact in full on hover, for a consumer that cuts it short", () => {
    render(<DidYouKnow fact={withLink} />);
    expect(screen.getByText(withLink.text)).toHaveAttribute("title", withLink.text);
  });

  it("shows a fact without a link", () => {
    render(<DidYouKnow fact={{ text: "Smarter speaks French." }} />);
    const note = screen.getByRole("complementary", { name: "Did you know?" });
    expect(note).toHaveTextContent("Smarter speaks French.");
    expect(within(note).queryByRole("link")).not.toBeInTheDocument();
  });

  it("has no styles of its own: the consumer's class names and icons", () => {
    render(
      <DidYouKnow
        fact={withLink}
        classNames={{ root: "root", title: "title", text: "text", link: "link" }}
        icon={<i data-testid="icon" />}
        linkIcon={<i data-testid="link-icon" />}
      />,
    );
    const note = screen.getByRole("complementary", { name: "Did you know?" });
    expect(note).toHaveClass("root");
    expect(screen.getByText("Did you know?")).toHaveClass("title");
    expect(screen.getByText(withLink.text)).toHaveClass("text");
    expect(screen.getByRole("link")).toHaveClass("link");
    expect(screen.getByText("Did you know?")).toContainElement(screen.getByTestId("icon"));
    expect(screen.getByRole("link")).toContainElement(screen.getByTestId("link-icon"));
  });
});
