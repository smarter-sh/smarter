// ----------------------------------------------------------------------------
// YTVideo Component.
// ----------------------------------------------------------------------------
import YouTube from "react-youtube";

import "./styles.css";

interface YTVideoProps {
  videoId: string;
}

function YTVideo({ videoId }: YTVideoProps) {

  return (
    <>
      <section aria-label="YTVideo" className="col-xl-6 mb-xl-10">
        <YouTube videoId={videoId} opts={{ width: "560", height: "315" }} />
      </section>
    </>
  );
}

export default YTVideo;
