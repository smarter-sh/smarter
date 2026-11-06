/**
 * The Doodle: the left panel of the web console's sign-in pages. The logo, the doodle of the day, its
 * caption, and the project's name and description. @smarter/console renders it, inside an element with
 * the smarter-doodle class.
 *
 * When a Smarter AI application chose or drew the doodle, a credit, with a link to how it works,
 * takes the place of the project's description.
 *
 * Until the doodle of the day arrives, and if it never does, the panel shows the base scene. App.css
 * styles the smarter-doodle-* classes.
 *
 * :param appContext: The root element's attributes.
 * :param timeZone: The visitor's time zone. The browser's, by default.
 */
import { useEffect, useState } from "react";
import { gettext } from "@smarter/common";

import { browserTimeZone, fetchDoodle } from "./lib/api";
import { loggerPrefix } from "./lib/const";
import type { AppContext, DoodleApiResponse } from "./lib/Types";
import "./App.css";

function App({ appContext, timeZone = browserTimeZone() }: { appContext: AppContext; timeZone?: string }) {
  const [doodle, setDoodle] = useState<DoodleApiResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchDoodle(appContext.apiUrl, timeZone, controller.signal)
      .then(setDoodle)
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        console.warn(`${loggerPrefix} showing the base scene, because the doodle of the day failed:`, error);
      });
    return () => controller.abort();
  }, [appContext.apiUrl, timeZone]);

  const imageUrl = doodle ? doodle.imageUrl : appContext.baseImageUrl;
  const altText = doodle ? doodle.altText : "";
  const showCaption = doodle !== null && doodle.showCaption && doodle.caption !== "";

  return (
    <>
      <a href={appContext.homeUrl} className="smarter-doodle-logo">
        <img alt="Logo" src={appContext.logoUrl} />
      </a>
      <figure
        className="smarter-doodle-figure"
        data-testid="smarter-doodle-figure"
        data-theme={doodle?.theme ?? "default"}
      >
        <img
          key={imageUrl}
          data-testid="smarter-doodle-image"
          className={loaded ? "smarter-doodle-image smarter-doodle-image-loaded" : "smarter-doodle-image"}
          src={imageUrl}
          alt={altText}
          onLoad={() => setLoaded(true)}
        />
        {showCaption && (
          <figcaption className="smarter-doodle-caption" data-testid="smarter-doodle-caption">
            {doodle.linkUrl ? (
              <a href={doodle.linkUrl} target="_blank" rel="noopener noreferrer">
                {doodle.caption}
              </a>
            ) : (
              doodle.caption
            )}
          </figcaption>
        )}
      </figure>
      <h1 className="smarter-doodle-title">{appContext.productName}</h1>
      {doodle?.aiCredit ? (
        <div className="smarter-doodle-description smarter-doodle-ai-credit" data-testid="smarter-doodle-ai-credit">
          {doodle.aiCredit === "drawn"
            ? gettext("Drawn by a Smarter AI application.")
            : gettext("Chosen by a Smarter AI application.")}{" "}
          <a href={doodle.learnHowUrl} target="_blank" rel="noopener">
            {gettext("Learn how")}
          </a>
        </div>
      ) : (
        <div className="smarter-doodle-description">
          {appContext.productDescription}{" "}
          <a href={appContext.projectUrl} target="_blank" rel="noopener">
            {gettext("Learn more")}
          </a>
        </div>
      )}
    </>
  );
}

export default App;
