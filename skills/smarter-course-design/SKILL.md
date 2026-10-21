---
name: smarter-course-design
description: Use when asked to design, write or extend a course, curriculum, syllabus, bootcamp, workshop or class plan for the Smarter Free Course Catalog in docs/source/smarter-instructors/example-courses (e.g. "add a micro course on Celery", "write a course design for MCP"). Covers building the course around real files and commits in github.com/smarter-sh repositories, the three formats (eight-hour classroom bootcamp, two-week and four-week online), graded assignments, two capstones, rubrics, prerequisites, recommended texts and further study, where every file goes, and the checker script.
---

# Smarter Course Design

The Free Course Catalog (`docs/source/smarter-instructors/example-courses/`)
holds several micro courses and master classes, published on docs.smarter.sh. Each
is a ready-to-teach course design: an instructor takes a plan, sets the dates,
and teaches it.

**The point of every course design is to showcase the Smarter code base.** A
course on Docker is not a generic Docker course with Smarter mentioned. It
teaches Docker _from_ Smarter's Dockerfile, Compose file and Makefile, and every
lecture, lab and assignment names the files and commits it uses. Students open
them in class. A course you could have written without reading this repository
is a failed course design.

## What to read first

1. `micro-courses/course-formats.rst`, in full. It defines the three formats,
   the standard bootcamp day, the standard live session, the grade weights, the
   rubric scale and the course policies. Plans refer to it; never restate it.
2. One complete existing course, all six files, closest to the new course's
   audience:

   | New course's students    | Copy                                                         |
   | ------------------------ | ------------------------------------------------------------ |
   | Non-programmers          | `prompt-engineering`, `ai-governance`                        |
   | Developers               | `agentic-development`, `backend-development`, `api-design`   |
   | Operations and platforms | `docker`, `kubernetes`, `infrastructure-as-code`             |
   | Code-reading, no coding  | `software-architecture` (its source section is "Principles") |

3. The `micro-courses.rst` table, to check that the subject isn't already
   covered. A new course that overlaps one should either narrow its scope or be
   a section added to the existing course. Ask the user when unsure.

The user's "a course with bootcamp, two-week and four-week formats" means a
**micro course**. Master classes (`master-classes/django-master-class`) are
longer, for experienced practitioners, with formats of their own; only build
one when asked for one by name, and copy the Django master class.

## Workflow

### 1. Build the inventory before the syllabus

Research first, outline second. The code decides what the course can teach.

- Find the subject in `smarter/smarter/` (apps, `lib/`, `common/`), the
  `Makefile`, `docker-compose.yml`, `helm/`, `.github/workflows/`, `skills/`,
  `docs/source/` (including the ADRs in `docs/source/adr/`) and the React
  workspace in `smarter/react/packages/`.
- Search the other public repositories, cloned next to this one
  (`../<repo>`; clone any that are missing):

  | Repository               | What's there                                                    |
  | ------------------------ | --------------------------------------------------------------- |
  | `smarter-infrastructure` | Terraform for AWS: EKS, networking, DNS, the production cluster |
  | `smarter-cli`            | The Go command-line interface, packaged for each OS             |
  | `smarter-python`         | The Python API client library on PyPI                           |
  | `smarter-deploy`         | The Docker quickstart for running the platform                  |
  | `smarter-helm`           | The published Helm chart (the source is `smarter/helm/charts/`) |
  | `smarter-vscode-yaml`    | The VS Code extension for manifest files                        |
  | `examples`               | Example manifests                                               |
  | `smarter.sh`             | The project's website (see below)                               |

  `smarter.sh` is not an example project, but its landing page runs four
  live integrations: built-in LLMClients chatting through Smarter Chat's
  embed script. It is the real-world example of embedding the chat in a web
  page (`src/common/chatbots.js`, `src/components/site/SmarterChatEmbed.jsx`).
  Smarter Chat itself, the React component, is in this repository, in
  `smarter/react/packages/smarter.sh-chat`. The `smarter-chat` and
  `web-integration-example` repositories are archived: don't link them.

  **`account-manager` is private. Never link it or describe its contents.**
  Check visibility with `gh repo list smarter-sh --json name,visibility`
  before linking any repository not in this table.

- Mine the history for teachable commits: `git log --grep=<topic>`,
  `git log -S<symbol>`, `git log --format='%h %s' -- <path>`. A good commit has
  a body that explains what was wrong, what changed and how it was tested.
  Bug fixes, refactors and "a mistake turned into a rule" make the best case
  studies.
- Count what you claim. "More than five thousand unit tests" or "ten custom
  middleware classes" must be true today; count with `grep`/`find` and prefer
  round, durable figures.

Write `source-code.txt` from this inventory **first**, then design lectures
around its rows. A topic with no row in it doesn't belong in the course, or
needs a row.

### 2. Write the six files

Six files per micro course, under `micro-courses/`. Skeletons for each are in
[references/course-anatomy.md](references/course-anatomy.md).

| File                       | Contents                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------- |
| `<slug>.rst`               | Overview: Why Smarter, What the course covers, Look at, Read, Exercises, plan toctree |
| `<slug>/bootcamp.rst`      | Classroom bootcamp plan, 8 hours                                                      |
| `<slug>/two-week.rst`      | Two-week online plan, 6 hours                                                         |
| `<slug>/four-week.rst`     | Four-week online plan, 12 hours                                                       |
| `<slug>/source-code.txt`   | Shared by all three plans via `.. include::`: the files and commits, in tables        |
| `<slug>/further-study.txt` | Shared by all three plans via `.. include::`: resources beyond the course             |

Write the bootcamp first (the tightest), then the four-week course (the
fullest), then cut the two-week course from it. Each plan stands alone: an
instructor reading only `two-week.rst` must be able to teach it.

### 3. Register the course

All four places, or the course is orphaned or the counts lie:

- `micro-courses.rst`: a table row (Course, Students, Programming) and a
  toctree entry, both in a sensible position by subject.
- `example-courses/index.rst`: the counts ("19 complete course designs",
  "18 short courses").
- `docs/source/index.rst`: the count of micro courses and the subject table
  that lists every course.
- `micro-courses/course-formats.rst` only if a cross-reference is useful.

`grep -rn "18 \|19 \|eighteen\|nineteen" docs/source/index.rst docs/source/smarter-instructor*.rst docs/source/smarter-instructors/example-courses/*.rst`
finds the counts.

### 4. Verify

```console
python3 skills/smarter-course-design/scripts/check-course.py <slug>
skills/smarter-sphinx-docs/scripts/check-docs.sh docs/source/smarter-instructors/example-courses/micro-courses/<slug>.rst docs/source/smarter-instructors/example-courses/micro-courses/<slug>/*.rst docs/source/smarter-instructors/example-courses/*.rst docs/source/index.rst
source venv/bin/activate && git ls-files -mo --exclude-standard docs/ | xargs pre-commit run --files
```

[scripts/check-course.py](scripts/check-course.py) checks the six files, the
plan sections, the number of assignments and capstones, that every rubric adds
up (20 or 100), that every GitHub link names a path or commit that exists on
`main` of its local clone, and that the course is registered. Run
`git -C ../<repo> fetch` first so `origin/main` is current. A `WARN` means the
path exists only on the current branch (usually `alpha`): the link 404s until
it is merged to `main`. Tell the user. `--all` checks every course. Don't build
the Sphinx docs.

## Hard links

Every reference to code is a link a student can click during class.

- **A file:** `` `image_search.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/image_search.py>`__ ``
- **A folder:** `` `apps/guardrail/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/guardrail>`__ ``
- **A commit:** full 40-character SHA in the URL, 9 characters in the text:
  `` `commit eeb7a7a19 <https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48>`__ ``
- **A pull request:** `` `pull request #775 <https://github.com/smarter-sh/smarter/pull/775>`__ ``
- **A docs page:** `` :doc:`/smarter-resources/smarter-budget` `` or
  `` :doc:`Budget </smarter-resources/smarter-budget>` ``, never a
  docs.smarter.sh URL. ADRs are `` :doc:`ADR 031 </adr/031-pydantic-over-json>` ``.

Rules: always `main`, never `alpha` or a SHA in a blob link; no line-number
anchors (they drift); anonymous links (`__`, two underscores) so repeated link
text doesn't clash; link text is the file name or a short path. Inside a
schedule cell, plain ` ``literal`` ` paths are fine when `source-code.txt`
links the same file; the schedule's intro sentence points there.

## Format constants

These come from `course-formats.rst`. The checker enforces the counts.

| Plan      | Lectures              | Hands-on                         | Assignments  | Capstone due   |
| --------- | --------------------- | -------------------------------- | ------------ | -------------- |
| Bootcamp  | 6 × 45 min            | 4 × 45-min labs + 30-min kickoff | 3 (labs 1–3) | One week after |
| Two-week  | 6 × 30 min, recorded  | 2 × 90-min live sessions         | 3            | Live session 2 |
| Four-week | 12 × 30 min, recorded | 4 × 90-min live sessions         | 4            | Live session 4 |

- Bootcamp schedule: exactly the eleven blocks of the standard day. Labs 1–3
  produce Assignments 1–3, Lab 4 is ungraded practice that leads into the
  capstone, block 11 is the capstone kickoff.
- Online schedules: three lectures then a live session per week. The last live
  session is capstone presentations. After the schedule table, one paragraph
  says when each assignment, the capstone proposal (four-week) and the
  capstone are due.
- Assignments are worth **20 points**, capstones **100**. Never restate grade
  weights or policies in a plan; a plan states only what differs.

## Content rules

**Learning objectives.** Five for a bootcamp or two-week plan, six for four
weeks, each starting with a verb that can be assessed ("Explain", "Write",
"Deploy", "Compare"). Every objective is assessed by an assignment or capstone.

**Technical prerequisites.** Bulleted, each starting **Required:**,
**Required by the end of week 1:**, **Helpful:** or **Not needed:**. Name the
Smarter setup (a shared instance run by the instructor, or Smarter from source
with `make init`) and when it must work: before a bootcamp, since there's no
time to fix laptops on the day. Link a free primer for anything a student may
lack (e.g. Learn YAML in Y minutes).

**At a Glance.** Students, Deployment, then Models or Workload as relevant,
then Cost: a dollar estimate per student, capped with a
:doc:`Budget </smarter-resources/smarter-budget>` when LLM calls are involved.

**Graded assignments.** Each is done in Smarter: a manifest applied, a change
in the student's fork with a pull request against the fork, an analysis that
cites files and commits. Give a two-sentence description, a **Turn in:** line,
and a rubric. Include a verification or honesty criterion wherever students
could take a tool's word for it.

**Capstones.** Exactly two, A and B, offering a real choice (e.g. build versus
analyze, or Smarter versus the student's own project). Each has a
**Learning objective.** paragraph, a description, **What students turn in:**
(bullets), and **How it is graded (100 points):**. The four-week course's
capstones are bigger than the two-week course's, and may differ entirely. A
capstone that contributes to Smarter must be agreed with the maintainers in a
GitHub issue first.

**Rubrics.** A four-column `list-table`, `:widths: 22 8 35 35`, columns
Criterion, Pts, Exemplary, Developing. Three to five criteria for an
assignment, four to six for a capstone. Weight points toward the learning
objective, not polish. Developing describes the most common way of falling
short, in a few words ("Took the agent's word for it."), not "partly meets".

**Recommended texts.** Bullets labeled **Pre-reading:**, **Required:** (with
the week, online only), **Reference:**, and **In the repository:**. Real books
only, with author, title, edition, publisher and year. If you aren't sure a
book exists as described, search for it or leave it out. Check books are on
O'Reilly Learning or widely held, as `course-formats.rst` asks instructors to.

**Further study (`further-study.txt`).** Five to eight bullets, each a bold
label for a kind of resource that suits the subject: **Official
documentation:**, **Standards:**, **Research:**, **Tools:**, **Community:**,
**Writing:**, and so on. Every course so far has **YouTube:** and
**Podcasts:**. Official docs, primary sources and long-lived channels. Never
invent a URL: cite a talk or paper by title, speaker and year when unsure of
its link. End with blog.smarter.sh when it has relevant posts.

## Style

The same voice as the rest of docs.smarter.sh (see `smarter-sphinx-docs`):
plain, specific, evergreen, no "new in" framing. 100-column lines. Headings `=`
page, `-` section, `~` subsection. Students' data is invented. No secrets,
account IDs or private hostnames: this repository is public. Cross-link
related courses with `:doc:` (Docker leads to Kubernetes, Backend to the
Django master class).

## Definition of done

- Six files, built from an inventory of real files and commits, with every
  path and commit checked by `check-course.py` (and any `WARN` reported).
- `check-docs.sh` and the pre-commit hooks pass on every changed file.
- The course is registered in all four places, and the counts are right.
- Your summary lists the repositories and commits the course draws on, any
  claim you counted, and any book or resource you couldn't confirm.
