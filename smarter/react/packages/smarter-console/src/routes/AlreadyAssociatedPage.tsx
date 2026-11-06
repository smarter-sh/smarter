/**
 * The page that the social sign-in pipeline redirects to, /account/already-associated/, when the Google or
 * GitHub account belongs to another of the platform's users.
 */
import { gettext } from "@smarter/common";
import { Link } from "react-router";

import { AuthCard } from "@/components/AuthCard";
import { LOGIN_PATH } from "@/lib/const";

export function AlreadyAssociatedPage() {
  return (
    <AuthCard title={gettext("Social Account Already Associated")}>
      <p className="text-center">
        {gettext("The social account you tried to associate is already linked to another user on this platform.")}
      </p>
      <p className="text-center mt-6 mb-0">
        <Link to={LOGIN_PATH}>{gettext("Back to sign in")}</Link>
      </p>
    </AuthCard>
  );
}
