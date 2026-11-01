/**
 * Prints the fact of the day as a Slack message, for .github/workflows/didYouKnow.yml, which pipes
 * it into scripts/slack_post.py. It is the same fact that the web console and smarter.sh show today
 * (midnight to midnight UTC).
 *
 * Run it with `npm run --silent slack:fact`, which bundles it with esbuild from source, so that no
 * package has to be built first. @smarter/common points at its source, and its css is left out.
 */
import { factOfTheDay } from "../src/lib/facts";
import { slackMessage } from "../src/lib/slack";

console.log(slackMessage(factOfTheDay()));
