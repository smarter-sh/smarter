import { describe, expect, it } from "vitest";

import { cookieMetaFactory, getCookie, inCookieDomain, setCookie } from "./cookie";

describe("inCookieDomain", () => {
  it("matches the domain, its subdomains, and Django's domain settings with a port or leading dot", () => {
    expect(inCookieDomain("localhost", "localhost")).toBe(true);
    expect(inCookieDomain("localhost", "localhost:9357")).toBe(true);
    expect(inCookieDomain("platform.smarter.sh", ".smarter.sh")).toBe(true);
    expect(inCookieDomain("alpha.platform.smarter.sh", "platform.smarter.sh")).toBe(true);
  });

  it("matches any hostname when the domain is empty or None", () => {
    expect(inCookieDomain("example.com", "")).toBe(true);
    expect(inCookieDomain("example.com", "None")).toBe(true);
    expect(inCookieDomain("example.com", undefined)).toBe(true);
  });

  it("does not match another domain", () => {
    expect(inCookieDomain("example.com", "smarter.sh")).toBe(false);
    expect(inCookieDomain("notsmarter.sh", "smarter.sh")).toBe(false);
  });
});

describe("getCookie and setCookie", () => {
  it("reads a cookie in the page's domain", () => {
    document.cookie = "csrftoken=abc123; path=/";
    expect(getCookie(cookieMetaFactory("csrftoken", null, "localhost"))).toBe("abc123");
  });

  it("returns the default for a missing cookie, or a cookie of another domain", () => {
    document.cookie = "csrftoken=abc123; path=/";
    expect(getCookie(cookieMetaFactory("missing", null, "localhost"), "default")).toBe("default");
    expect(getCookie(cookieMetaFactory("csrftoken", null, "smarter.sh"), "default")).toBe("default");
  });

  it("prefers the cookie's preset value", () => {
    document.cookie = "csrftoken=abc123; path=/";
    expect(getCookie(cookieMetaFactory("csrftoken", null, "localhost", "preset"))).toBe("preset");
  });

  it("sets a cookie, then deletes it", () => {
    const cookie = cookieMetaFactory("session_key", 60_000, "localhost");
    setCookie(cookie, "the-session");
    expect(getCookie(cookie)).toBe("the-session");
    setCookie(cookie, "");
    expect(getCookie(cookie)).toBeNull();
  });

  it("saves booleans as text", () => {
    const cookie = cookieMetaFactory("debug", 60_000, "localhost");
    setCookie(cookie, false);
    expect(getCookie(cookie)).toBe("false");
    setCookie(cookie, null);
  });
});
