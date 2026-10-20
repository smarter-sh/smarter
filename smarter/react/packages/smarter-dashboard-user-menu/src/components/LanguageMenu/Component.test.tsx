import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { appContext } from "@/mocks/fixtures";

import LanguageMenu from "@/components/LanguageMenu/Component";

const props = {
  languages: appContext.languages,
  currentLanguage: "es",
  setLanguageUrl: "/i18n/setlang/",
  nextUrl: "/dashboard/?tab=1",
  csrfToken: "token",
};

describe("LanguageMenu", () => {
  it("renders nothing with fewer than two languages", () => {
    const { container } = render(<LanguageMenu {...props} languages={[{ code: "en", name: "English" }]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists every language in its own name, and posts the choice to set_language with the page to return to", async () => {
    const user = userEvent.setup();
    render(<LanguageMenu {...props} />);
    const toggle = screen.getByRole("button", { name: /Language/ });
    expect(toggle).toHaveTextContent("Español");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const form = screen.getByRole("form", { name: "Language" });
    expect(form).toHaveAttribute("action", "/i18n/setlang/");
    expect(form).toHaveAttribute("method", "post");
    expect(screen.getByDisplayValue("/dashboard/?tab=1")).toHaveAttribute("name", "next");
    expect(screen.getByDisplayValue("token")).toHaveAttribute("name", "csrfmiddlewaretoken");
    for (const language of appContext.languages) {
      const button = screen.getByRole("button", { name: language.name });
      expect(button).toHaveAttribute("type", "submit");
      expect(button).toHaveAttribute("name", "language");
      expect(button).toHaveValue(language.code);
      expect(button).toHaveAttribute("lang", language.code);
    }
    expect(screen.getByRole("button", { name: "Español" })).toHaveAttribute("aria-current", "true");
  });

  it("matches a regional variant of the current language to its generic language", () => {
    render(<LanguageMenu {...props} currentLanguage="fr-CA" />);
    expect(screen.getByRole("button", { name: /Language/ })).toHaveTextContent("Français");
  });

  it("matches a language code whatever its case", () => {
    render(<LanguageMenu {...props} currentLanguage="pt-BR" />);
    expect(screen.getByRole("button", { name: /Language/ })).toHaveTextContent("Português Brasileiro");
  });
});
