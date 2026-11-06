/**
 * The console: its session, then its routes. The routes render only once the session has loaded, so that
 * every page can rely on it.
 */
import { gettext } from "@smarter/common";
import { RouterProvider, type createBrowserRouter } from "react-router";

import { SessionProvider } from "@/session/SessionProvider";
import { useConsoleSession } from "@/session/context";

type Router = ReturnType<typeof createBrowserRouter>;

function SessionGate({ router }: { router: Router }) {
  const { session, error, refresh } = useConsoleSession();
  if (error && !session) {
    return (
      <div role="alert" className="text-center py-10">
        <p>{gettext("The console couldn't reach the server.")}</p>
        <button type="button" className="btn btn-sm btn-primary" onClick={() => void refresh()}>
          {gettext("Try again")}
        </button>
      </div>
    );
  }
  if (!session) {
    return (
      <div role="status" className="text-center py-10">
        {gettext("Loading...")}
      </div>
    );
  }
  return <RouterProvider router={router} />;
}

export default function App({ router }: { router: Router }) {
  return (
    <SessionProvider>
      <SessionGate router={router} />
    </SessionProvider>
  );
}
