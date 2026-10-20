/**
 * The user menu, at the top right of every console page.
 *
 * The user's profile image is a button that opens and closes it; their email shows on hover, and names
 * the button for screen readers. A click outside the menu, or Escape, closes it. For a signed-in user,
 * the menu has their name and email, the Language item (with two or more languages), Change Profile
 * Image, Remove Profile Image, Change Profile (with two or more profiles), Welcome Tour and Sign Out.
 * An anonymous request gets the Language item and Sign In.
 *
 * Welcome Tour opens the welcome dialog, the @smarter/welcome app, which listens for clicks on elements
 * with the data-smarter-welcome-open attribute.
 *
 * :param appContext: The root element's attributes.
 * :param onSwitched: Passed to the Change Profile dialog. Reloads the page by default.
 */
import { useEffect, useId, useRef, useState } from "react";
import { getCookie, gettext } from "@smarter/common";

import ChangeProfile from "@/components/ChangeProfile";
import LanguageMenu from "@/components/LanguageMenu";
import MenuHeader from "@/components/MenuHeader";
import ProfileImageItems from "@/components/ProfileImageItems";
import type { AppContext } from "@/lib/Types";

interface UserMenuProps {
  appContext: AppContext;
  onSwitched?: () => void;
}

function UserMenu({ appContext, onSwitched }: UserMenuProps) {
  const { sessionContext, isAuthenticated, user, urls } = appContext;
  const [open, setOpen] = useState(false);
  const [changingProfile, setChangingProfile] = useState(false);
  const [profileImageUrl, setProfileImageUrl] = useState(appContext.profileImageUrl);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const fileInputId = useId();
  const csrfToken = getCookie({ name: sessionContext.csrfCookieName, domain: sessionContext.cookieDomain }) || "";

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const openChangeProfile = () => {
    setOpen(false);
    setChangingProfile(true);
  };

  const closeChangeProfile = () => {
    setChangingProfile(false);
    buttonRef.current?.focus();
  };

  const label = isAuthenticated ? user.email || user.username : gettext("Sign In");

  return (
    <div ref={rootRef} className="position-relative">
      <button
        ref={buttonRef}
        type="button"
        className="btn p-0 border-0 bg-transparent symbol symbol-circle symbol-35px symbol-md-40px"
        title={label}
        aria-label={label}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen(!open)}
      >
        <img className="smarter-profile-image" alt="" src={profileImageUrl} />
      </button>
      <div
        id={menuId}
        className={`menu menu-sub menu-sub-dropdown menu-column menu-rounded menu-gray-800 menu-state-bg menu-state-color fw-semibold py-4 fs-6 w-275px${open ? " show" : ""}`}
        style={{ position: "absolute", top: "calc(100% + 0.75rem)", right: 0 }}
      >
        {isAuthenticated && (
          <>
            <MenuHeader
              user={user}
              profileImageUrl={profileImageUrl}
              accountName={appContext.accountName}
              showAccount={appContext.userProfileCount > 1}
              fileInputId={fileInputId}
            />
            <div className="separator my-2"></div>
          </>
        )}
        <LanguageMenu
          languages={appContext.languages}
          currentLanguage={appContext.currentLanguage}
          setLanguageUrl={urls.setLanguage}
          nextUrl={urls.next}
          csrfToken={csrfToken}
        />
        {isAuthenticated && (
          <>
            <ProfileImageItems
              sessionContext={sessionContext}
              apiUrl={urls.profileImageApi}
              fileInputId={fileInputId}
              onChange={setProfileImageUrl}
            />
            {appContext.userProfileCount > 1 && (
              <div className="menu-item px-5">
                <button
                  type="button"
                  className="menu-link px-5 w-100 border-0 bg-transparent"
                  aria-haspopup="dialog"
                  onClick={openChangeProfile}
                >
                  {gettext("Change Profile")}
                </button>
              </div>
            )}
            <div className="menu-item px-5 mt-1">
              <button
                type="button"
                className="menu-link px-5 w-100 border-0 bg-transparent"
                data-smarter-welcome-open="true"
                onClick={() => setOpen(false)}
              >
                {gettext("Welcome Tour")}
              </button>
            </div>
            <div className="menu-item px-5">
              <a href={urls.logout} className="menu-link px-5">
                {gettext("Sign Out")}
              </a>
            </div>
          </>
        )}
        {!isAuthenticated && (
          <div className="menu-item px-5">
            <a href={urls.login} className="menu-link px-5">
              {gettext("Sign In")}
            </a>
          </div>
        )}
      </div>
      {changingProfile && (
        <ChangeProfile
          sessionContext={sessionContext}
          userProfilesApiUrl={urls.userProfilesApi}
          userProfileSelectApiUrl={urls.userProfileSelectApi}
          onClose={closeChangeProfile}
          onSwitched={onSwitched}
        />
      )}
    </div>
  );
}

export default UserMenu;
