/**
 * The fact of the day as a Slack message, which .github/workflows/didYouKnow.yml posts to #general
 * every day, through scripts/slack-fact-of-the-day.ts.
 */
import type { DidYouKnowFact } from "./facts";

/** Escapes the three characters that Slack's mrkdwn treats as control characters. */
export function slackEscape(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * Formats a fact as a Slack message, in mrkdwn: a lightbulb, Did you know?, the fact, and its link.
 *
 * :param fact: The fact.
 * :returns: The message.
 */
export function slackMessage(fact: DidYouKnowFact): string {
  const lines = [":bulb: *Did you know?*", slackEscape(fact.text)];
  if (fact.link) {
    lines.push(`<${fact.link.url}|${slackEscape(fact.link.label)}>`);
  }
  return lines.join("\n");
}
