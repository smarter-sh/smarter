/**
 * The note below the title of this package's development page and stories: Did you know?, and the fact
 * of the day, in small text on one line. In the web console, @smarter/console renders DidYouKnow in its
 * header, with its own class names, while the session's didYouKnow flag (the
 * enable_web_console_did_you_know waffle switch) is on.
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
