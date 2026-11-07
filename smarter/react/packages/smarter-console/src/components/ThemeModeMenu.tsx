/**
 * The header's theme mode menu: Light, Dark or System. It does what the theme's own JavaScript does, which the
 * console doesn't load: it applies the mode, and stores it where that JavaScript does, so that the console and the
 * pages that Django still renders from templates/base.html open in the same mode. See lib/theme.
 */
import { gettext, useDropdown } from "@smarter/common";
import { useState } from "react";

import { setThemeMode, themeMode, type ThemeMode } from "@/lib/theme";

interface ModeOption {
  mode: ThemeMode;
  label: string;
  /** A Keenicons outline icon. */
  icon: string;
}

function modeOptions(): ModeOption[] {
  return [
    { mode: "light", label: gettext("Light"), icon: "ki-night-day" },
    { mode: "dark", label: gettext("Dark"), icon: "ki-moon" },
    { mode: "system", label: gettext("System"), icon: "ki-screen" },
  ];
}

export function ThemeModeMenu() {
  const { open, setOpen, toggle, rootRef, buttonRef, menuId } = useDropdown();
  const [mode, setMode] = useState<ThemeMode>(themeMode);
  const options = modeOptions();
  const current = options.find((option) => option.mode === mode) ?? options[0];

  const choose = (option: ModeOption) => {
    setThemeMode(option.mode);
    setMode(option.mode);
    setOpen(false);
    buttonRef.current?.focus();
  };

  return (
    <div ref={rootRef} className="position-relative">
      <button
        ref={buttonRef}
        type="button"
        className="btn btn-icon btn-custom btn-icon-muted btn-active-light btn-active-color-primary w-35px h-35px w-md-40px h-md-40px"
        title={gettext("Theme")}
        aria-label={gettext("Theme")}
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={toggle}
      >
        <i className={`ki-outline ${current.icon} fs-1`} aria-hidden="true" />
      </button>
      <div
        id={menuId}
        className={`menu menu-sub menu-sub-dropdown menu-column menu-rounded menu-title-gray-700 menu-icon-gray-500 menu-active-bg menu-state-color fw-semibold py-4 fs-base w-150px${open ? " show" : ""}`}
        style={{ position: "absolute", top: "calc(100% + 0.75rem)", right: 0 }}
      >
        {options.map((option) => (
          <div key={option.mode} className="menu-item px-3 my-0">
            <button
              type="button"
              className={`menu-link px-3 py-2 w-100 border-0 bg-transparent${option.mode === mode ? " active" : ""}`}
              aria-pressed={option.mode === mode}
              onClick={() => choose(option)}
            >
              <span className="menu-icon">
                <i className={`ki-outline ${option.icon} fs-2`} aria-hidden="true" />
              </span>
              <span className="menu-title">{option.label}</span>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
