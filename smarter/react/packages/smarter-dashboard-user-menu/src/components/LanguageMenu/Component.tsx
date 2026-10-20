/**
 * The user menu's Language item, which lists the console's languages, each in its own name, and posts
 * the choice to Django's set_language view, which returns to this page in that language.
 *
 * Clicking the item opens and closes the list below it. It renders nothing with fewer than two languages.
 *
 * :param languages: The console's languages.
 * :param currentLanguage: The code of the page's language.
 * :param setLanguageUrl: Django's set_language view.
 * :param nextUrl: The page to return to.
 * :param csrfToken: The CSRF token that the form posts.
 */
import { useId, useState } from "react";
import { gettext } from "@smarter/common";

import type { Language } from "@/lib/Types";

interface LanguageMenuProps {
  languages: Language[];
  currentLanguage: string;
  setLanguageUrl: string;
  nextUrl: string;
  csrfToken: string;
}

function LanguageMenu({ languages, currentLanguage, setLanguageUrl, nextUrl, csrfToken }: LanguageMenuProps) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (languages.length < 2) return null;
  const current =
    languages.find((language) => language.code.toLowerCase() === currentLanguage.toLowerCase()) ??
    languages.find((language) => language.code.toLowerCase() === currentLanguage.toLowerCase().split("-")[0]);

  return (
    <div className={`menu-item px-5${open ? " show" : ""}`}>
      <button
        type="button"
        className="menu-link px-5 w-100 border-0 bg-transparent"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen(!open)}
      >
        <span className="menu-title position-relative text-start">
          {gettext("Language")}
          {current && (
            <span
              className="fs-8 rounded bg-light px-3 py-2 position-absolute translate-middle-y top-50 end-0 text-nowrap"
              lang={current.code}
            >
              {current.name}
            </span>
          )}
        </span>
      </button>
      <div id={listId} className="menu-sub menu-sub-accordion pt-2">
        <form action={setLanguageUrl} method="post" className="w-100" aria-label={gettext("Language")}>
          <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
          <input type="hidden" name="next" value={nextUrl} />
          {languages.map((language) => (
            <div className="menu-item" key={language.code}>
              <button
                type="submit"
                name="language"
                value={language.code}
                lang={language.code}
                aria-current={language === current ? "true" : undefined}
                className={`menu-link d-flex px-5 ps-10 w-100 border-0 bg-transparent text-nowrap${language === current ? " active" : ""}`}
              >
                {language.name}
              </button>
            </div>
          ))}
        </form>
      </div>
    </div>
  );
}

export default LanguageMenu;
