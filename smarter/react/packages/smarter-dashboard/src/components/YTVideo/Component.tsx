/**
 * YTVideo dashboard widget.
 *
 * This component renders an embedded YouTube video inside a dashboard section
 * using the react-youtube player wrapper.
 *
 * :param videoId: YouTube video identifier used to load the embedded player.
 * :type videoId: str
 *
 * :returns: A JSX fragment containing a single responsive dashboard video
 *     section.
 * :rtype: JSX.Element
 *
 * :example:
 *
 *     <YTVideo videoId="YtVxkjHzZrE" />
 */
import YouTube from "react-youtube";

import "./styles.css";

interface YTVideoProps {
  videoId: string;
}

function YTVideo({ videoId }: YTVideoProps) {

  return (
    <>
      <section aria-label="YTVideo" className="col-xl-6 mb-xl-10 d-none d-md-table-cell">
        <YouTube videoId={videoId} opts={{ width: "560", height: "315" }} />
      </section>
    </>
  );
}

export default YTVideo;
