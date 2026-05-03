// ----------------------------------------------------------------------------
// YTVideo Component.
// ----------------------------------------------------------------------------
import "./styles.css";


interface YTVideoProps {
  apiUrl: string;
}

function YTVideo({ apiUrl }: YTVideoProps) {

  return (
    <>
      <section className="yt-video" aria-label="YTVideo">
        <h4>Hello World {apiUrl}</h4>
      </section>
    </>
  );
}

export default YTVideo;
