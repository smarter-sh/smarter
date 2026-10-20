import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { appContext } from "@/mocks/fixtures";

import App from "@/App";

describe("App", () => {
  it("renders the user menu", async () => {
    const user = userEvent.setup();
    render(<App appContext={appContext} />);
    await user.click(screen.getByRole("button", { name: "ada@example.edu" }));
    expect(screen.getByRole("link", { name: "Sign Out" })).toBeInTheDocument();
  });
});
