# Anatomy of the example post

[Claude Code Shipped Our Product Roadmap in 8 Days. Here's What Made It Work](https://blog.smarter.sh/2026/10/10/claude-code-large-django-codebase/),
published October 10, 2026. About 6,000 words of prose, roughly 26 minutes.
This file describes what each part of it does and quotes short lines that
show its voice. It isn't a copy of the post; fetch the post itself with
`scripts/fetch-post.sh` and read it in full before you write.

## The one idea

An AI coding agent multiplies whatever it finds in a codebase. The post
states it as a pair of series:

> In a healthy codebase, the series is telescopic. [...] Contrastingly, in an
> unhealthy codebase, the series is geometric, with a ratio greater than one.

Every later section comes back to the metaphor in its last line, e.g. "Tests
are the cancellation in the telescope", "That's the geometric series", "A
mistake that isn't written down is a term in the series, waiting to be
multiplied."

## Section by section

The published example opens with a TLDR jump link. Don't copy it: the user no
longer wants TLDR links, and a post's first sentence must name its technology
(see SKILL.md, section 3).

| Section                                         | What it does                                                                                                                                                |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Opening, four paragraphs                        | States the idea, sets out the two series, raises the stakes ("an involuntary career change on your part"), and closes with "This is the story about [...]". |
| 8 days in October                               | The headline facts: 8 days, about 20 prompts, 1 to 4 hours each, six releases in a table that links each release post.                                      |
| The codebase that Claude built                  | Sizes in a table (lines, apps, tests, coverage, docs pages, ADRs, hooks), so the reader knows this isn't a toy.                                             |
| Who built what?                                 | Splits credit honestly between humans, Copilot and Claude Code, with git blame percentages per package and three stated qualifications.                     |
| What "subsystem" means here / Why this split... | Explains the human-built foundation in concrete terms (SAM, brokers, journal, tenancy, secrets, settings), then ties it to the telescope.                   |
| Success factors #1 to #5                        | One `###` per factor, each with `####` subsections, real code samples, numbers and a closing line that returns to the metaphor.                             |
| What went wrong                                 | The October 6 DNS outage: what the agent did, the cost (about 20 minutes offline), the small fix, and the lasting fix (a skill).                            |
| Quantitative results                            | The 25 times multiplier, derived from contributor-graph numbers, then three caveats as "First ... Second ... Third ...".                                    |
| If you want the same result on your codebase    | Seven bulleted takeaways "in rough order of payoff".                                                                                                        |
| Closing thoughts                                | Where the roadmap stands, a last return to the metaphor, "Until then, happy Smartering!" and five links.                                                    |

## Voice, in the post's own lines

- **Candor about the author's own mistakes:** "Sheesh, it was downright
  embarrassing!" and "the blame unfairly attributes it to him. 😬"
- **Candor about the agent's mistakes, with the cost:** "One wrong value,
  copied, then copied again. We were offline for nearly 20 minutes."
- **A flourish, then facts:** "That's cataclysmic, it's apocalyptic, and it
  will likely end in an involuntary career change on your part." Followed by a
  plain paragraph.
- **A rare word, used with a wink:** "at the risk of sounding thoroughly
  ultracrepidarian".
- **An opinion that has changed, said as such:** "My thoughts have evolved
  about how much testing is 'enough'. [...] Nowadays, I think more is
  better. 🤩"
- **Short closing lines:** "An agent that can run your code converges. An
  agent that can't is guessing."
- **Neutral on the agent:** "A 25-times multiplier is neutral. It makes a
  telescoping series converge 25 times faster. But it could just as
  haphazardly make a geometric series diverge 25 times faster."

## Numbers the post established

Later posts may reuse these, and should quote them exactly:

- Roadmap finished in 8 days, about 20 prompts, six minor releases
  (v0.15 to v0.20, September 30 to October 10, 2026).
- About 130 bugs fixed while raising coverage to about 97%.
- About 240,000 lines of Python excluding migrations, 21 Django apps, about
  5,300 Python tests and 1,300 React tests, 30 ADRs, 15 skills.
- The author: about 750,000 lines over three and a half years, about 4,000
  lines a week, about 1,500 lines of source a week.
- Claude Code: 110,000 lines in 8 days, about 40,000 lines of source in one
  week, about 25 times the author's pace.

## What to do differently in a shorter post

The example is a flagship essay. A follow-up of about 10 minutes keeps the
same parts but shrinks them: one opening, one summary table, one section per
case, a single numbers section, a short takeaways list and the closing.
It doesn't need a sizes table or a credit split unless the story turns on it.
