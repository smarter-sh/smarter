import { describe, expect, it } from "vitest";

import { repositoryUrl } from "./repository";

describe("repositoryUrl", () => {
  it("accepts the https url of a repository on any host", () => {
    expect(repositoryUrl("https://github.com/smarter-sh/smarter")).toBe("https://github.com/smarter-sh/smarter");
    expect(repositoryUrl("https://github.com/smarter-sh/smarter/")).toBe("https://github.com/smarter-sh/smarter");
    expect(repositoryUrl("https://bitbucket.org/someone/smarter")).toBe("https://bitbucket.org/someone/smarter");
    expect(repositoryUrl("https://gitlab.com/group/subgroup/smarter")).toBe(
      "https://gitlab.com/group/subgroup/smarter",
    );
    expect(repositoryUrl("https://git.example.com:8443/smarter")).toBe("https://git.example.com:8443/smarter");
  });

  it("rejects a value that isn't safe to link to", () => {
    for (const value of [
      "",
      "not a url",
      "http://github.com/smarter-sh/smarter",
      "https://github.com/",
      "https://user:token@github.com/smarter-sh/smarter",
      "https://github.com/smarter-sh/smarter?tab=readme",
      "https://github.com/smarter-sh/smarter#readme",
      "https://github.com/smarter-sh/smar%22ter",
      "javascript:alert(1)",
    ]) {
      expect(repositoryUrl(value)).toBeNull();
    }
  });
});
