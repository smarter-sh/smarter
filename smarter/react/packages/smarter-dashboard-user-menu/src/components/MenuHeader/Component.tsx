/**
 * The top of the user menu: the user's profile image, name, role badge and email, and, for a user
 * with more than one profile, the account that the console acts as.
 *
 * Clicking the image chooses a new one to upload, through the Change Profile Image item's file input.
 *
 * :param user: Who the user is.
 * :param profileImageUrl: The image that represents them.
 * :param accountName: The account of the profile that the console acts as, shown when showAccount is set.
 * :param showAccount: Whether to show the account, for a user with more than one profile.
 * :param fileInputId: The id of the profile image's file input, or undefined when the image can't be changed.
 */
import { gettext } from "@smarter/common";

import type { MenuUser } from "@/lib/Types";

interface MenuHeaderProps {
  user: MenuUser;
  profileImageUrl: string;
  accountName: string;
  showAccount: boolean;
  fileInputId?: string;
}

function MenuHeader({ user, profileImageUrl, accountName, showAccount, fileInputId }: MenuHeaderProps) {
  const image = <img className="smarter-profile-image" alt={gettext("Profile Image")} src={profileImageUrl} />;
  const fullName = [user.firstName, user.lastName].filter(Boolean).join(" ");
  return (
    <div className="menu-item px-3">
      <div className="menu-content d-flex align-items-center px-3">
        {fileInputId ? (
          <label
            htmlFor={fileInputId}
            className="symbol symbol-50px me-5 cursor-pointer"
            title={gettext("Change Profile Image")}
          >
            {image}
          </label>
        ) : (
          <div className="symbol symbol-50px me-5">{image}</div>
        )}
        <div className="d-flex flex-column min-w-0">
          <div className="fw-bold d-flex align-items-center fs-5">
            <span className="text-truncate">{user.username}</span>
            {user.isSuperuser ? (
              <span className="badge badge-light-success fw-bold fs-8 px-2 py-1 ms-2">{gettext("Superuser")}</span>
            ) : (
              user.isStaff && (
                <span className="badge badge-light-success fw-bold fs-8 px-2 py-1 ms-2">{gettext("Staff")}</span>
              )
            )}
          </div>
          <span className="fw-semibold text-muted fs-7 text-truncate">{user.email}</span>
          {fullName && <div className="text-muted d-flex align-items-center fs-7">{fullName}</div>}
          {showAccount && accountName && (
            <div className="text-muted d-flex align-items-center fs-7 text-truncate" title={gettext("Account")}>
              {accountName}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MenuHeader;
