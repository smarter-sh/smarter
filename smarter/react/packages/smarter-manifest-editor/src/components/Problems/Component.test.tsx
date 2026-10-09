import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { fakeEditor } from "@/mocks/fakeEditor";
import { SECRET_YAML } from "@/mocks/fixtures";
import type { ManifestError } from "@/lib/validation";

import Problems from "./Component";

const valueOffset = SECRET_YAML.indexOf("value:");

const samError: ManifestError = {
  source: "sam",
  message: "value must be at least 32 characters",
  offset: valueOffset,
  loc: ["spec", "config", "value"],
};
const syntaxError: ManifestError = { source: "yaml", message: "bad indentation", offset: 0, loc: [] };

describe("Problems", () => {
  it("says that it is checking the manifest", () => {
    render(<Problems errors={[]} isValidating editor={null} />);
    expect(screen.getByText("Checking the manifest…")).toBeInTheDocument();
  });

  it("says when there are no problems", () => {
    render(<Problems errors={[]} isValidating={false} editor={null} />);
    expect(screen.getByText("No problems")).toBeInTheDocument();
  });

  it("lists each problem, with its line and path", () => {
    const { monacoEditor } = fakeEditor(SECRET_YAML);
    render(<Problems errors={[samError, syntaxError]} isValidating={false} editor={monacoEditor} />);
    expect(screen.getByText("2 problems")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^Line 9\s*spec.config.value: value must be at least 32 characters$/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Line 1\s*bad indentation$/ })).toBeInTheDocument();
  });

  it("moves the editor's cursor to a problem", async () => {
    const user = userEvent.setup();
    const { editor, monacoEditor } = fakeEditor(SECRET_YAML);
    render(<Problems errors={[samError]} isValidating={false} editor={monacoEditor} />);
    expect(screen.getByText("1 problem")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /value must be/ }));
    expect(editor.revealLineInCenter).toHaveBeenCalledWith(9);
    expect(editor.setPosition).toHaveBeenCalledWith({ lineNumber: 9, column: 5 });
    expect(editor.focus).toHaveBeenCalled();
  });

  it("lists problems without lines before the editor mounts", async () => {
    const user = userEvent.setup();
    render(<Problems errors={[samError]} isValidating={false} editor={null} />);
    const problem = screen.getByRole("button", { name: "spec.config.value: value must be at least 32 characters" });
    await user.click(problem);
    expect(problem).toBeInTheDocument();
  });
});
