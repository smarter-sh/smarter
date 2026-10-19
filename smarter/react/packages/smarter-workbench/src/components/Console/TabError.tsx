/** Why a Console tab couldn't load its data. */
import { gettext } from "@smarter/common";

export default function TabError({ error }: { error: string }) {
  return (
    <div className="alert alert-danger m-0" role="alert">
      {gettext("This tab couldn't load. Reload the page to try again.")} {error}
    </div>
  );
}
