/**
 * The Extensions console, /extensions and /extensions/<slug>: @smarter/extension-console's list, or an extension's
 * page, with a context from the session. A superuser manages extensions; everyone else sees them read-only, and the
 * api refuses an extension that the user's account may not see. The context is made once per session and page.
 */
import { ExtensionConsole } from "@smarter/extension-console";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";

import { djangoSessionContext } from "@/lib/djangoSession";
import { EXTENSIONS_API_URL, EXTENSIONS_PATH } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

export function ExtensionsPage() {
  const { session } = useConsoleSession();
  const { slug } = useParams();
  const navigate = useNavigate();
  const context = useMemo(() => {
    if (!session) return null;
    return {
      session: djangoSessionContext(session, EXTENSIONS_API_URL),
      apiUrl: EXTENSIONS_API_URL,
      // the Django page's url, which the api's links use too.
      listUrl: `${EXTENSIONS_PATH}/`,
      slug,
      canEdit: session.user?.isSuperuser ?? false,
    };
  }, [session, slug]);
  if (!context) return null;
  return <ExtensionConsole context={context} navigate={(url) => void navigate(url)} />;
}
