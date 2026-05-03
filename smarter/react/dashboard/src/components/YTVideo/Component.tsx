// ----------------------------------------------------------------------------
// YTVideo Component.
// ----------------------------------------------------------------------------
import YouTube from 'react-youtube';

import "./styles.css";


interface YTVideoProps {
  apiUrl: string;
}

function YTVideo({ apiUrl }: YTVideoProps) {
  console.log("YTVideo component received apiUrl:", apiUrl);

  return (
    <>
      <section className="yt-video" aria-label="YTVideo">
              {/* begin::Col yt video 1 */}
      <div className="col-xl-6 mb-xl-10">
        <YouTube videoId="YtVxkjHzZrE" opts={{ width: '560', height: '315' }} />
      </div>
      {/* end::Col yt video 1 */}

      </section>
    </>
  );
}

export default YTVideo;
