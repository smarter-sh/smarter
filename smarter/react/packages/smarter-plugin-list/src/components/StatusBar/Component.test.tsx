import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "@/components/StatusBar/Component";

describe("StatusBar", () => {
  it.each([
    [true, /^Ready:/],
    [false, /^Not ready:/],
  ])("shows whether it is ready: %s", (ready, title) => {
    render(<StatusBar plugin={makeObject(1, { ready } as never)} />);
    expect(screen.getByTitle(title)).toBeInTheDocument();
  });
});
