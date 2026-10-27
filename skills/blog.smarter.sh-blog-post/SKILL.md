---
name: blog.smarter.sh-blog-post
description: Use when asked to write a blog post, article, essay, prologue, follow-up, retrospective, lesson-learned or how-to for blog.smarter.sh that is not a release announcement, e.g. a story about how Smarter was built, what an AI coding agent did in the codebase, a design mistake and how it was fixed, or an engineering opinion. Covers finding the post's one idea, gathering evidence from commit bodies and git history (including measuring how a pattern grew across release tags), back-of-the-envelope productivity arithmetic, the structure of a long-form post, the author's voice as shown in the published example, reading-time targets, public-repo hygiene, and what to check before handing it over. For a post that announces a Smarter version, use blog.smarter.sh-release-announcement instead.
---

# blog.smarter.sh Blog Post

A long-form post on [blog.smarter.sh](https://blog.smarter.sh) tells a true
story from Smarter's development and draws one lesson from it, for developers
who build with AI coding agents or with Django. It is a Markdown file the user
pastes into the blog. It is not part of the docs, and it is not committed to
the repository.

The style and content guide is a published post that the user wrote:
[Claude Code Shipped Our Product Roadmap in 8 Days. Here's What Made It Work](https://blog.smarter.sh/2026/10/10/claude-code-large-django-codebase/).
[references/example-anatomy.md](references/example-anatomy.md) walks through
it section by section and quotes the lines that set its voice. Read that
first. Then read the post itself in full, because a summary loses the voice:

```bash
skills/blog.smarter.sh-blog-post/scripts/fetch-post.sh \
  https://blog.smarter.sh/2026/10/10/claude-code-large-django-codebase/ \
  <scratchpad>/example-post.md
```

WebFetch returns only a summary of a page, so use the script, not WebFetch, to
read a post.

## Story or state? Ask which kind of post it is

Not every post is a story. A how-to, a design walkthrough, or a post about what
an agent can do ("6 uses of Claude Code", "how Smarter's list views work")
describes **the current state and what it makes possible**, in the present
tense. For those posts:

- Don't tell how it got there. No before/after numbers, no "it was slow, now
  it's fast", no "we started at 75% and reached 96%", no bugs found along the
  way, no timeline of commits, no "what went wrong" section.
- Use evidence as present facts: what the design does, how it works, what it
  enables, and what someone needs in place to get the same result. A commit is
  cited as an example of the capability, not as a step in a story.
- Leave out the numbers-with-caveats section, which exists to support a
  story's claims.
- Every sentence has to help explain the problem, how it's solved, or how to
  use the solution. Leave out statements about how widely or how much it's
  used: adoption counts ("148 decorated functions in 67 files"), tables of
  uses per package, line counts of the module, and "it's the one/preferred way
  Smarter does X". They praise the thing rather than explain it, and the
  numbers go stale with the next commit. Show how it's used with the patterns
  and their code instead. The user removed exactly these from the
  `@cache_results()` how-to.

The user has had to correct this repeatedly. Unless the request asks for a
story, a retrospective or a lesson learned, assume it is a state post. The rest
of this skill (structure, "what went wrong", productivity arithmetic) applies
to story posts.

## 1. Find the one idea

A post argues one idea, and everything in it is evidence for that idea. Write
the idea down in one sentence before you write anything else, e.g. "an agent
multiplies whatever patterns it finds, good or bad".

- If a metaphor carries the idea (the example uses telescoping versus
  geometric series), introduce it in the opening and come back to it at the
  end of each section. Don't mix in a second metaphor.
- If the post follows an earlier one (a prologue, a sequel, a correction),
  fetch the earlier post, reuse its terms and numbers exactly, link it in the
  first paragraph, and summarize it in two or three sentences rather than
  re-explaining it.
- The user's request usually names the points to emphasize, e.g. "bring
  attention to the 25x multiple". Those are requirements. Give each one its
  own section or table, not a passing mention.

## 2. Gather the evidence

The post's credibility comes from specifics that a reader could check. Keep a
notes file in your scratchpad with each number and the command that produced
it.

1. **Commit bodies.** `git log -1 --format='%H%n%an%n%ad%n%n%B' --date=iso <sha>`
   and `git show --shortstat --format= <sha>`. Smarter's commit bodies explain
   what was wrong, what changed, how it was tested and what was left undone.
   They are the raw material for the story.
2. **Timelines.** Commit times (`--date=iso`) put a story in order and bound
   how long the work took. When sessions overlap, the commits don't say how
   time was split between them. Say so rather than invent a split.
3. **Growth over time.** To show a pattern spreading, count it at each release
   tag, not just today:

   ```bash
   for ref in $(git tag --sort=creatordate | grep -E '^v0\.[0-9]+\.0$') HEAD; do
     printf '%s %s %s\n' "$ref" "$(git log -1 --format=%ad --date=short "$ref")" \
       "$(git grep -c 'dict\[str, Any\]' "$ref" -- 'smarter/smarter/*.py' | awk -F: '{s+=$NF} END {print s+0}')"
   done
   ```

   `git log -S'<text>' --format='%h %ad %an %s' --date=short` finds the
   commits that added or removed it. `git grep -c` counts lines, not
   occurrences, so say "lines that contain".

4. **Attribution.** Agent commits appear as `Claude`, `Claude Code (...)` or
   `Claude Opus ...`, and some agent work was committed under the user's name.
   Treat author counts as a floor for the agent, and say so in the post.
5. **Code samples** come from the repository, trimmed, with their path. Never
   write one from memory.
6. **Links.** Docs pages
   (`https://docs.smarter.sh/en/latest/<path>.html`, from the `.rst` under
   `docs/source/`), ADRs, skills and source files on GitHub
   (`https://github.com/smarter-sh/smarter/tree/main/...`), commits
   (`https://github.com/smarter-sh/smarter/commit/<sha>`), and external
   projects at first mention.
7. **The user's own experience.** Only the user knows what they knew, decided
   or forgot. Use what they told you, in their words, and don't add feelings
   or memories they didn't describe.

### Back-of-the-envelope arithmetic

When a post estimates productivity, show the inputs, the formula and the
result, and check it a second way. The baselines published in the example
post are:

| Measure                                            | Value                       |
| -------------------------------------------------- | --------------------------- |
| The author's long-run pace, all lines (code, docs) | about 4,000 lines a week    |
| The author's long-run pace, source code            | about 1,500 lines a week    |
| Claude Code's pace during the 8-day roadmap sprint | about 25 times the author's |
| A working week, for converting hours to weeks      | 40 hours                    |

- By time: agent hours × 25 = equivalent human hours; ÷ 40 = weeks.
- By lines: count insertions with `git show --numstat`, excluding generated
  files (JSON Schema, lockfiles, migrations), then divide by the weekly pace.
- When the two disagree, report both and explain why. Line counts undercount
  refactors, where each changed line is a decision.

## 3. Structure

In this order:

1. **Title:** clear, not clever. It must name the technology the post is
   about (OpenAPI, Docker, Kubernetes, Pydantic, Claude Code, ...), so a reader
   scanning a list knows the subject at a glance, e.g. "Smarter's OpenAPI
   Contract: One Extensibility Model for Python, Go, React and VS Code". A
   title that names only Smarter's own concepts ("Smarter's Clients Don't Know
   What a Broker Is") was rejected by the user as unclear. A claim or story is
   fine after the technology's name, never instead of it. Then a date line. Both stay in
   the Markdown only: the H1 becomes the WordPress title, and the publishing
   script leaves both out of the post's content, because the theme prints the
   title and date (see `blog.smarter.sh-publish`).
2. **The first sentence names the technology** and says what the post is
   about, e.g. "Smarter publishes its whole REST API as one OpenAPI 3.1
   document". Don't open with a general problem, a metaphor or a scene and
   name the subject paragraphs later: a reader who stops after one sentence
   must know what the post covers. The user rejected an opening whose first
   mention of OpenAPI was in its third paragraph.
   **No TLDR jump link** (`(TLDR? [Click here](#tldr) ...)`) and no section
   headed "TLDR". The user doesn't want them. Head the takeaways "Takeaways".
3. **The rest of the opening,** one to three paragraphs: the problem, the
   stakes and why now. No warm-up sentences.
4. **The story, with a table early on** that summarizes it (releases, fixes,
   sizes, times). A reader who stops there should still have the gist.
5. **Body sections** as `##`, with `###` and occasionally `####` beneath.
   Question headings are fine ("Who built what?"). End each section with a
   short line that ties it back to the idea, e.g. "An agent that can run your
   code converges. An agent that can't is guessing."
6. **What went wrong.** A success story needs its failure, told plainly with
   its cost. A story about a failure needs what was done so that it can't
   recur.
7. **The numbers,** in a table, followed by their caveats as "First ...
   Second ... Third ...".
8. **Takeaways** the reader can apply to their own codebase, as bullets in
   rough order of payoff.
9. **Closing thoughts,** one or two paragraphs, then "Until then, happy
   Smartering!" and a short list of links: Smarter on GitHub, the docs, the
   blog, the ADRs and anything the post leaned on.

## 4. Voice

The posts are written in the voice of Lawrence McDaniel, Smarter's creator.

- **First person** for opinions, decisions and anecdotes ("My thoughts have
  evolved about how much testing is enough"). The example sometimes says "the
  author"; prefer "I".
- **Candid and self-deprecating** about mistakes, with their real cost
  ("We were offline for nearly 20 minutes"). Credit honestly: humans built the
  subsystems, GitHub Copilot wrote many docstrings and tests, Claude Code built
  the newer apps. Don't inflate anyone's share.
- **Plain sentences and exact numbers,** with an occasional flourish: a
  rare word used with a wink ("ultracrepidarian", "behooves"), or a burst of
  hyperbole followed at once by facts. One or two flourishes per post, not one
  per paragraph.
- **A few emoji** (😬 🤩 😱 ✨) at the end of a sentence, as a reaction. About
  one per thousand words. (Release announcements use none.)
- Call the agent **Claude Code**, linked at first mention to
  `https://claude.com/product/claude-code`.
- Avoid marketing words ("game-changing", "seamless", "revolutionary"),
  sentences that announce what's coming ("In this section we'll look at"),
  and stacked adjectives.
- Use headings, not bold lines, as section labels, and blank lines around
  lists. The user's editor flags bold-as-heading (MD036) and lists without
  blank lines (MD032).

When Claude Code drafts a post about its own work, it still writes in the
user's voice, because the post goes out under the user's name. Whether to say
that an agent drafted it is the user's decision. Raise it in your reply,
especially if an earlier post says that the author wrote it.

## 5. Length

Reading time is prose words outside code blocks ÷ 230. Measure it:

```bash
skills/blog.smarter.sh-blog-post/scripts/reading-time.sh ~/desktop/blog-<slug>.md
```

A 10-minute post is about 2,300 words of prose. The example runs about 26
minutes, which suits a flagship essay but not a follow-up. When the user
gives a target, land within a minute of it, and cut detail before you cut
evidence.

## 6. Public-repo hygiene

The post is published, and this skill lives in a public repository. Commit
bodies sometimes name production hosts, customer tenants, databases or
namespaces. Never copy them into the post: write "a production host" or
`<your-smarter>`. A security fix may be described once its commit is public,
but describe what was exposed, not how to exploit an unpatched deployment.

## 7. Before handing it over

- Every number traces to a command in your notes, or to the earlier post.
- Every linked commit is on `main` (`git branch -r --contains <sha>` lists
  `origin/main`). In smarter-infrastructure and other repositories, the same
  change can exist under different SHAs on other branches, and a link to one of
  those breaks once the branch is deleted. Find the `main` copy with
  `git log origin/main --format='%H %ad %s' --date=short -- <path>`.
- Every commit SHA exists (`git cat-file -e <sha>^{commit}`), every GitHub
  path exists at `HEAD`, and every docs link's `.rst` exists under
  `docs/source/`. You can't check that the published URLs work, so say so.
- The reading time is measured, not guessed.
- Save the post to `~/desktop/blog-<slug>.md`, unless the user names another
  place. Never save it inside the repository or only in your scratchpad.
- In your reply, list what to review before publishing: estimates and how
  they were made, anything said in the user's voice that they didn't tell you,
  the date, and the question of disclosure.
- The post needs a featured image. The project has an Envato account for
  stock illustrations, so suggest a few search terms for the user to pick one
  from. `blog.smarter.sh-publish` has the details.
