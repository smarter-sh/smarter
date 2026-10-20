/**
 * The Change Profile dialog, which the user menu's Change Profile item opens for a user with more than
 * one profile, e.g. a student who is enrolled in two courses at once.
 *
 * It lists the user's profiles, newest first, with each one's account number, account name and the date
 * that it was created. The profile that the console acts as is marked Current. Switch, on another one,
 * makes the console act as it, for the rest of the session, and then reloads the page, so that
 * everything on it belongs to the chosen account. Escape, Close and a click on the backdrop close it.
 *
 * :param sessionContext: The cookies and headers of the requests.
 * :param userProfilesApiUrl: Lists the user's profiles.
 * :param userProfileSelectApiUrl: Chooses the profile that the console acts as.
 * :param onClose: Called when the user closes the dialog.
 * :param onSwitched: Called once the console acts as the chosen profile. Reloads the page by default.
 */
import { useEffect, useState } from "react";
import { formatDateTime, gettext, interpolate, Modal, type SessionContext } from "@smarter/common";

import { postUserProfiles } from "@/lib/api";
import { loggerPrefix } from "@/lib/const";
import type { UserProfileChoice } from "@/lib/Types";

interface ChangeProfileProps {
  sessionContext: SessionContext;
  userProfilesApiUrl: string;
  userProfileSelectApiUrl: string;
  onClose: () => void;
  onSwitched?: () => void;
}

const reload = () => window.location.reload();

function ChangeProfile({
  sessionContext,
  userProfilesApiUrl,
  userProfileSelectApiUrl,
  onClose,
  onSwitched = reload,
}: ChangeProfileProps) {
  const [userProfiles, setUserProfiles] = useState<UserProfileChoice[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [switching, setSwitching] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    postUserProfiles(sessionContext, userProfilesApiUrl)
      .then((data) => {
        if (!cancelled) setUserProfiles(data.userProfiles);
      })
      .catch((err: Error) => {
        console.error(loggerPrefix, "Error fetching", userProfilesApiUrl, err);
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionContext, userProfilesApiUrl]);

  const switchTo = (userProfile: UserProfileChoice) => {
    setError(null);
    setSwitching(userProfile.id);
    postUserProfiles(sessionContext, userProfileSelectApiUrl, { userProfileId: userProfile.id })
      .then((data) => {
        setUserProfiles(data.userProfiles);
        onSwitched();
      })
      .catch((err: Error) => {
        console.error(loggerPrefix, "Error fetching", userProfileSelectApiUrl, err);
        setError(err.message);
        setSwitching(null);
      });
  };

  return (
    <Modal show title={gettext("Change Profile")} onClose={onClose}>
      <p className="text-muted fs-7">
        {gettext("You belong to more than one account. Choose the one that the console acts as, for this session.")}
      </p>
      {error && (
        <div className="alert alert-danger py-2 fs-7" role="alert">
          {error}
        </div>
      )}
      {!userProfiles && !error && (
        <div className="text-muted" role="status">
          {gettext("Loading…")}
        </div>
      )}
      {userProfiles && (
        <div className="table-responsive">
          <table className="table table-row-dashed align-middle fs-7 mb-0">
            <thead>
              <tr className="text-muted fw-bold text-uppercase fs-8">
                <th scope="col">{gettext("Account Number")}</th>
                <th scope="col">{gettext("Account Name")}</th>
                <th scope="col">{gettext("Profile Created")}</th>
                <th scope="col">
                  <span className="visually-hidden">{gettext("Switch")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {userProfiles.map((userProfile) => (
                <tr key={userProfile.id} aria-current={userProfile.isCurrent ? "true" : undefined}>
                  <td className="text-nowrap font-monospace">{userProfile.accountNumber}</td>
                  <td>{userProfile.accountName}</td>
                  <td className="text-nowrap">{formatDateTime(userProfile.createdAt, "date")}</td>
                  <td className="text-end">
                    {userProfile.isCurrent ? (
                      <span className="badge badge-light-success">{gettext("Current")}</span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-sm btn-light-primary text-nowrap"
                        disabled={switching !== null}
                        aria-label={interpolate(gettext("Switch to %(account)s"), { account: userProfile.accountName })}
                        onClick={() => switchTo(userProfile)}
                      >
                        {switching === userProfile.id ? gettext("Switching…") : gettext("Switch")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

export default ChangeProfile;
