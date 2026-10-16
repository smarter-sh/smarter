import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { currentLanguage, gettext, interpolate, interpolateNodes, ngettext, npgettext, pgettext } from "./i18n";

/** A Spanish catalog shaped like the one that Django's JavaScriptCatalog defines. */
const spanish = {
  gettext: (msgid: string) => ({ Secrets: "Secretos" })[msgid] ?? msgid,
  ngettext: (singular: string, plural: string, count: number) => (count === 1 ? `es:${singular}` : `es:${plural}`),
  pgettext: (context: string, msgid: string) => `es:${context}:${msgid}`,
  npgettext: (context: string, singular: string, plural: string, count: number) =>
    `es:${context}:${count === 1 ? singular : plural}`,
};

describe("i18n", () => {
  afterEach(() => {
    delete window.django;
    document.documentElement.lang = "";
  });

  describe("without a catalog", () => {
    it("returns the English source text", () => {
      expect(gettext("Secrets")).toBe("Secrets");
      expect(pgettext("verb", "Clone")).toBe("Clone");
    });

    it("chooses the English plural form by count", () => {
      expect(ngettext("%(count)s secret", "%(count)s secrets", 1)).toBe("%(count)s secret");
      expect(ngettext("%(count)s secret", "%(count)s secrets", 2)).toBe("%(count)s secrets");
      expect(npgettext("list", "one", "many", 1)).toBe("one");
      expect(npgettext("list", "one", "many", 0)).toBe("many");
    });
  });

  describe("with Django's catalog", () => {
    it("translates through window.django", () => {
      window.django = spanish;
      expect(gettext("Secrets")).toBe("Secretos");
      expect(ngettext("secret", "secrets", 1)).toBe("es:secret");
      expect(ngettext("secret", "secrets", 3)).toBe("es:secrets");
      expect(pgettext("verb", "Clone")).toBe("es:verb:Clone");
      expect(npgettext("list", "one", "many", 2)).toBe("es:list:many");
    });
  });

  describe("interpolate", () => {
    it("replaces named placeholders, in any order", () => {
      expect(interpolate("%(b)s then %(a)s", { a: "A", b: 2 })).toBe("2 then A");
    });

    it("leaves a placeholder without a value as it is", () => {
      expect(interpolate("Hello %(name)s", { name: undefined })).toBe("Hello %(name)s");
      expect(interpolate("Hello %(name)s", {})).toBe("Hello %(name)s");
    });
  });

  describe("interpolateNodes", () => {
    it("puts React elements where the message's placeholders are", () => {
      render(
        <p>{interpolateNodes("Delete %(name)s from %(where)s?", { name: <strong>alpha</strong>, where: "here" })}</p>,
      );
      expect(screen.getByText("alpha").tagName).toBe("STRONG");
      expect(screen.getByText(/^Delete/)).toHaveTextContent("Delete alpha from here?");
    });

    it("leaves a placeholder without a value as it is", () => {
      render(<p>{interpolateNodes("%(missing)s", {})}</p>);
      expect(screen.getByText("%(missing)s")).toBeInTheDocument();
    });
  });

  describe("currentLanguage", () => {
    it("reads the lang attribute of the page", () => {
      document.documentElement.lang = "es";
      expect(currentLanguage()).toBe("es");
    });

    it("defaults to English", () => {
      expect(currentLanguage()).toBe("en");
    });
  });
});
