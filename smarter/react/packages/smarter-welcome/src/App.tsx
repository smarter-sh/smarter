/**
 * The Smarter welcome dialog.
 *
 * The console's base template mounts this app on every page, for signed-in users. The dialog opens by
 * itself once each time the user signs in, while its Show at startup box is ticked (``appContext.show``),
 * and again whenever they click an element with the ``data-smarter-welcome-open`` attribute, such as the
 * user menu's Welcome Tour item.
 *
 * Opening it loads its links from the welcome api. When the user closes it, or reaches its last step,
 * whose links leave the page, it tells the welcome dismiss api the box's choice, if the api doesn't
 * know it yet: unticked, the dialog doesn't open by itself again, on any device; either way, not again
 * in this session. Closing it returns the focus to where it was before it opened.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchDjangoUrl, gettext, interpolate } from "@smarter/common";

import WelcomeDialog from "@/components/WelcomeDialog";
import { loggerPrefix } from "@/lib/const";
import type { AppContext, WelcomeApiResponse, WelcomeUrls } from "@/lib/Types";

/** The attribute of the elements that open the dialog, e.g. the user menu's Welcome Tour item. */
export const OPEN_ATTRIBUTE = "data-smarter-welcome-open";

async function post(appContext: AppContext, url: string, body: object = {}): Promise<WelcomeApiResponse> {
  const response = await fetchDjangoUrl(appContext.sessionContext, url, JSON.stringify(body));
  if (!response.ok) throw new Error(interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
  return (await response.json()) as WelcomeApiResponse;
}

function App({ appContext }: { appContext: AppContext }) {
  const [open, setOpen] = useState(appContext.show);
  const [urls, setUrls] = useState<WelcomeUrls | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAtStartup, setShowAtStartup] = useState(appContext.showAtStartup);
  // what the dismiss api has recorded, or is recording: whether the dialog was closed in this session,
  // and the Show at startup box.
  const recorded = useRef({ closed: !appContext.show, showAtStartup: appContext.showAtStartup });
  // the element that had the focus before the dialog opened, which gets it back when the dialog closes.
  const opener = useRef<HTMLElement | null>(null);

  const openDialog = useCallback(() => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setOpen(true);
  }, []);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target instanceof Element ? event.target.closest(`[${OPEN_ATTRIBUTE}]`) : null;
      if (!target) return;
      event.preventDefault();
      openDialog();
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [openDialog]);

  useEffect(() => {
    if (!open || urls) return;
    let cancelled = false;
    post(appContext, appContext.apiUrl)
      .then((data) => {
        if (!cancelled) setUrls(data.urls);
      })
      .catch((err: Error) => {
        console.error(loggerPrefix, "Error fetching", appContext.apiUrl, err);
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [appContext, open, urls]);

  const dismiss = useCallback(() => {
    const previous = recorded.current;
    if (previous.closed && previous.showAtStartup === showAtStartup) return;
    recorded.current = { closed: true, showAtStartup };
    post(appContext, appContext.dismissApiUrl, { showAtStartup }).catch((err: Error) => {
      // the dialog opens again on the next page, with the box as it was. Nothing else is lost.
      console.error(loggerPrefix, "Error fetching", appContext.dismissApiUrl, err);
      recorded.current = previous;
    });
  }, [appContext, showAtStartup]);

  const close = useCallback(() => {
    setOpen(false);
    dismiss();
    opener.current?.focus();
    opener.current = null;
  }, [dismiss]);

  if (!open) return null;
  return (
    <WelcomeDialog
      firstName={appContext.firstName}
      logoUrl={appContext.logoUrl}
      illustrationsUrl={appContext.illustrationsUrl}
      urls={urls}
      error={error}
      showAtStartup={showAtStartup}
      onShowAtStartupChange={setShowAtStartup}
      onLastStep={dismiss}
      onClose={close}
    />
  );
}

export default App;
