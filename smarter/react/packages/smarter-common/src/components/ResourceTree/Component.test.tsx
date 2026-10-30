import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ResourceTree from "./Component";
import { leafTree, lockedTree, stackademyTree } from "../../mocks/resourceTree";

describe("ResourceTree", () => {
  it("shows a card for every resource, beneath the resource that uses it", () => {
    render(<ResourceTree tree={stackademyTree} />);
    const tree = screen.getByRole("list", { name: "The resources that this LLMClient is built from" });
    expect(within(tree).getByRole("article", { name: "LLMClient stackademy_sql" })).toBeInTheDocument();
    expect(within(tree).getAllByRole("article").length).toBeGreaterThan(5);
  });

  it("keeps which resources are collapsed itself, when it isn't controlled", async () => {
    const user = userEvent.setup();
    render(<ResourceTree tree={stackademyTree} label="Stackademy's resources" />);
    const before = screen.getAllByRole("article").length;
    const [toggle] = screen.getAllByRole("button", { name: /^Hide what / });
    await user.click(toggle);
    expect(screen.getAllByRole("article").length).toBeLessThan(before);
    expect(screen.getByRole("list", { name: "Stackademy's resources" })).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: /^Show what / })[0]);
    expect(screen.getAllByRole("article")).toHaveLength(before);
  });

  it("calls onToggle, when it's controlled", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<ResourceTree tree={stackademyTree} collapsed={new Set()} onToggle={onToggle} />);
    await user.click(screen.getAllByRole("button", { name: /^Hide what / })[0]);
    expect(onToggle).toHaveBeenCalledWith(expect.stringMatching(/^0\.\d+$/));
  });

  it("shows an LLMClient that uses nothing, and a resource that the user may not read", () => {
    const { unmount } = render(<ResourceTree tree={leafTree} />);
    expect(screen.getAllByRole("article")).toHaveLength(1);
    unmount();
    render(<ResourceTree tree={lockedTree} />);
    expect(screen.getByText("You can't read this resource")).toBeInTheDocument();
  });

  it("opens collapsed, with defaultCollapsed: the LLMClient and the resources that it uses directly", async () => {
    const user = userEvent.setup();
    render(<ResourceTree tree={stackademyTree} defaultCollapsed />);
    const direct = stackademyTree.children.length;
    expect(screen.getAllByRole("article")).toHaveLength(1 + direct);
    expect(screen.queryAllByRole("button", { name: /^Hide what / })).toHaveLength(0);
    await user.click(screen.getAllByRole("button", { name: /^Show what / })[0]);
    expect(screen.getAllByRole("article").length).toBeGreaterThan(1 + direct);
  });
});
