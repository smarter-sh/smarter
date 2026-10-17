import { describe, expect, it } from "vitest";

import { banner, duration, ended } from "@/lib/banner";
import { sessionInfo } from "@/mocks/fixtures";

describe("duration", () => {
  it("is in minutes below two hours, and in hours above", () => {
    expect(duration(60)).toBe("1 minute");
    expect(duration(30 * 60)).toBe("30 minutes");
    expect(duration(90 * 60)).toBe("90 minutes");
    expect(duration(3 * 3600)).toBe("3 hours");
  });
});

describe("banner", () => {
  it("is terminal lines, and names the host, the user and the limits", () => {
    const text = banner(sessionInfo);
    expect(text.endsWith("\r\n")).toBe(true);
    expect(text).not.toMatch(/[^\r]\n/);
    expect(text).toContain("smarter-app-7d9f8c6b5-x2kqp");
    expect(text).toContain("when the server restarts, or is redeployed or scaled down,");
    expect(text).toContain("after 30 minutes without input, and after 8 hours in any case.");
  });
});

describe("ended", () => {
  it("explains every reason, and offers a new session", () => {
    expect(ended("exited", 0)).toContain("The shell exited with status 0.");
    expect(ended("exited", null)).toContain("status ?.");
    expect(ended("expired", null)).toContain("time limit");
    expect(ended("failed", null)).toContain("could not start a shell");
    expect(ended("refused", null)).toContain("refused the connection");
    for (const reason of ["exited", "idle", "expired", "failed", "refused", "disconnected"] as const) {
      expect(ended(reason, 1)).toContain("Press Enter to start a new session.");
    }
  });
});
