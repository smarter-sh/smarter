/** The page of a route that the console doesn't have. */
import { gettext } from "@smarter/common";
import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <section className="text-center py-10">
      <h1 className="fs-2 fw-bold mb-4">{gettext("Page not found")}</h1>
      <Link to="/" className="btn btn-sm btn-primary">
        {gettext("Return Home")}
      </Link>
    </section>
  );
}
