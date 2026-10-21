import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CATALOGS } from "@/catalogs.gen";
import {
  LANGUAGES,
  activateLanguage,
  currentLanguage,
  gettext,
  interpolate,
  interpolateNodes,
  matchLanguage,
  ngettext,
  npgettext,
  pgettext,
  resolveLanguage,
} from "./i18n";

afterEach(() => {
  document.documentElement.lang = "";
  activateLanguage();
});

describe("matchLanguage", () => {
  it("matches a language, or its generic language, whatever its case", () => {
    expect(LANGUAGES).toEqual(["en", "es", "fr", "pt-br"]);
    expect(matchLanguage("es")).toBe("es");
    expect(matchLanguage("ES-mx")).toBe("es");
    expect(matchLanguage("es-419")).toBe("es");
    expect(matchLanguage("fr_CA")).toBe("fr");
    expect(matchLanguage(" en-US ")).toBe("en");
    expect(matchLanguage("pt-br")).toBe("pt-br");
    expect(matchLanguage("pt-BR")).toBe("pt-br");
    expect(matchLanguage("pt_BR")).toBe("pt-br");
    // a language that only has a regional catalog gets it for every variant
    expect(matchLanguage("pt")).toBe("pt-br");
    expect(matchLanguage("pt-PT")).toBe("pt-br");
  });

  it("matches nothing for other languages, or none", () => {
    expect(matchLanguage("de")).toBeNull();
    expect(matchLanguage("")).toBeNull();
    expect(matchLanguage(null)).toBeNull();
    expect(matchLanguage(undefined)).toBeNull();
  });
});

describe("resolveLanguage", () => {
  it("prefers the requested language, then the page's, then the browser's, then English", () => {
    document.documentElement.lang = "fr-FR";
    expect(resolveLanguage("es-MX")).toBe("es");
    expect(resolveLanguage("de")).toBe("fr");
    expect(resolveLanguage()).toBe("fr");
    document.documentElement.lang = "";
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE", "es-AR"]);
    expect(resolveLanguage()).toBe("es");
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["de-DE"]);
    expect(resolveLanguage()).toBe("en");
  });
});

describe("activateLanguage", () => {
  it("translates into the activated language from then on", () => {
    expect(activateLanguage("es")).toBe("es");
    expect(currentLanguage()).toBe("es");
    expect(gettext("Start a new chat")).toBe("Iniciar un chat nuevo");
    expect(activateLanguage("fr-CA")).toBe("fr");
    expect(gettext("Start a new chat")).toBe("Démarrer un nouveau chat");
    // the web console's pt-br, whose catalog is pt_BR
    expect(activateLanguage("pt-br")).toBe("pt-br");
    expect(gettext("Start a new chat")).toBe("Iniciar um novo chat");
    expect(activateLanguage(null)).toBe("en");
    expect(gettext("Start a new chat")).toBe("Start a new chat");
  });

  it("starts with the page's language", async () => {
    document.documentElement.lang = "fr";
    vi.resetModules();
    const i18n = await import("./i18n");
    expect(i18n.currentLanguage()).toBe("fr");
  });
});

describe("gettext and friends", () => {
  it("return the English source text without a translation", () => {
    activateLanguage("es");
    expect(gettext("Not a message of Smarter Chat")).toBe("Not a message of Smarter Chat");
    expect(ngettext("one thing", "%(count)s things", 1)).toBe("one thing");
    expect(ngettext("one thing", "%(count)s things", 2)).toBe("%(count)s things");
    expect(pgettext("button", "Not a message")).toBe("Not a message");
    expect(npgettext("list", "one row", "%(count)s rows", 1)).toBe("one row");
    expect(npgettext("list", "one row", "%(count)s rows", 3)).toBe("%(count)s rows");
  });

  it("choose the plural form by the language's plural rule", () => {
    const singular = "%(provider)s %(model)s with %(count)s additional tool";
    const plural = "%(provider)s %(model)s with %(count)s additional tools";
    activateLanguage("es");
    expect(ngettext(singular, plural, 0)).toBe("%(provider)s %(model)s con %(count)s herramientas adicionales");
    expect(ngettext(singular, plural, 1)).toBe("%(provider)s %(model)s con %(count)s herramienta adicional");
    // in French, 0 is singular.
    activateLanguage("fr");
    expect(ngettext(singular, plural, 0)).toBe("%(provider)s %(model)s avec %(count)s outil supplémentaire");
    expect(ngettext(singular, plural, 2)).toBe("%(provider)s %(model)s avec %(count)s outils supplémentaires");
    activateLanguage("en");
    expect(ngettext(singular, plural, 0)).toBe(plural);
  });

  it("translate messages in a context", () => {
    activateLanguage("es");
    expect(pgettext("button", "Code")).toBe("Código");
    expect(pgettext("other", "Code")).toBe("Code");
  });

  it("translate plural messages in a context, and fall back to English for a missing plural form", () => {
    const messages = CATALOGS.fr.messages;
    messages["list\u0004one row"] = ["une ligne", ""];
    try {
      activateLanguage("fr");
      expect(npgettext("list", "one row", "%(count)s rows", 1)).toBe("une ligne");
      expect(npgettext("list", "one row", "%(count)s rows", 2)).toBe("%(count)s rows");
    } finally {
      delete messages["list\u0004one row"];
    }
  });
});

describe("interpolate", () => {
  it("replaces named placeholders, wherever the translation puts them", () => {
    expect(interpolate("%(assistant)s : %(step)s", { assistant: "Stanley", step: "searching" })).toBe(
      "Stanley : searching",
    );
    expect(interpolate("%(count)s of %(count)s", { count: 2 })).toBe("2 of 2");
  });

  it("leaves a placeholder without a value, so that the mistake shows", () => {
    expect(interpolate("Close %(label)s", {})).toBe("Close %(label)s");
    expect(interpolate("Close %(label)s", { label: null })).toBe("Close %(label)s");
  });
});

describe("interpolateNodes", () => {
  it("puts React nodes into a sentence", () => {
    render(<p>{interpolateNodes("Delete %(name)s now, %(missing)s?", { name: <strong>Stanley</strong> })}</p>);
    expect(screen.getByText("Stanley").tagName).toBe("STRONG");
    expect(screen.getByText(/Delete/)).toHaveTextContent("Delete Stanley now, %(missing)s?");
  });
});
