import "@/components/Hero/styles.css";
import { gettext } from "@smarter/common";

function Hero() {
  return (
    <>
      <h3>{gettext("Server Logs")}</h3>
    </>
  );
}

export default Hero;
