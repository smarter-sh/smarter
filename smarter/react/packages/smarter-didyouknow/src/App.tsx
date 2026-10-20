/**
 * The note below the web console's title: Did you know?, and the fact of the day, in small text on one
 * line. The title bar, templates/dashboard/header.html, includes it on every console page while the
 * enable_web_console_did_you_know waffle switch is active.
 *
 * It is a consumer of this package's DidYouKnow component, as the welcome dialog is, and its styles
 * are its own, in App.css.
 *
 * :param date: The moment whose day picks the fact. Now, by default.
 */
import DidYouKnow from "./components/DidYouKnow/Component";
import { factOfTheDay } from "./lib/facts";
import "./App.css";

function App({ date = new Date() }: { date?: Date }) {
  return (
    <DidYouKnow
      fact={factOfTheDay(date)}
      classNames={{
        root: "smarter-didyouknow-header",
        title: "smarter-didyouknow-header-title",
        text: "smarter-didyouknow-header-text",
        link: "smarter-didyouknow-header-link",
      }}
    />
  );
}

export default App;
