/**
 * The user menu's Change Profile Image and Remove Profile Image items.
 *
 * Change Profile Image opens the browser's file chooser, and uploads the chosen PNG, JPEG, GIF or WebP
 * file, which replaces any earlier upload. Remove Profile Image removes it, and the console falls back
 * to the image from the oauth provider, if any, else the default one. The user's own image takes
 * precedence over the oauth provider's. Either way, the menu shows the new image at once; a rejected
 * upload shows the api's reason below the items.
 *
 * :param sessionContext: The cookies of the requests.
 * :param apiUrl: The profile image api, smarter.apps.account.views.dashboard.profile_image.
 * :param fileInputId: The id of the file input, which the menu header's image is a label for too.
 * :param onChange: Called with the url of the image that the console shows now.
 */
import { useState, type ChangeEvent } from "react";
import { gettext, type SessionContext } from "@smarter/common";

import { sendProfileImage } from "@/lib/api";
import { loggerPrefix } from "@/lib/const";

interface ProfileImageItemsProps {
  sessionContext: SessionContext;
  apiUrl: string;
  fileInputId: string;
  onChange: (profileImageUrl: string) => void;
}

/** The image formats that the profile image api accepts. SVG isn't one: it can carry script. */
const ACCEPT = "image/png,image/jpeg,image/gif,image/webp";

function ProfileImageItems({ sessionContext, apiUrl, fileInputId, onChange }: ProfileImageItemsProps) {
  const [error, setError] = useState<string | null>(null);

  const send = (method: "POST" | "DELETE", body?: FormData) => {
    setError(null);
    sendProfileImage(sessionContext, apiUrl, method, body)
      .then(onChange)
      .catch((err: Error) => {
        console.error(loggerPrefix, "Error sending the profile image to", apiUrl, err);
        setError(err.message);
      });
  };

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("profile_image", file);
    send("POST", form);
    event.target.value = "";
  };

  return (
    <>
      <input id={fileInputId} type="file" accept={ACCEPT} className="d-none" onChange={handleFile} />
      <div className="menu-item px-5">
        <label htmlFor={fileInputId} className="menu-link px-5">
          {gettext("Change Profile Image")}
        </label>
      </div>
      <div className="menu-item px-5">
        <button type="button" className="menu-link px-5 w-100 border-0 bg-transparent" onClick={() => send("DELETE")}>
          {gettext("Remove Profile Image")}
        </button>
      </div>
      {error && (
        <div className="menu-item px-5">
          <div className="menu-content px-5 py-1 text-danger fs-7" role="alert">
            {error}
          </div>
        </div>
      )}
    </>
  );
}

export default ProfileImageItems;
