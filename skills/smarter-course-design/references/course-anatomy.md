# Anatomy of a Micro Course

Skeletons of the six files, taken from the existing courses. `<...>` marks what
you fill in. Paths are relative to
`docs/source/smarter-instructors/example-courses/micro-courses/`. When a
skeleton and the newest existing course disagree, the course wins: read
`agentic-development/` and `docker/` in full alongside this file.

## `<slug>.rst`: the overview

```rst
<Subject Title, in Title Case>
==============================

**Why Smarter.** <Two or three paragraphs. Start with what courses on this subject usually lack,
then show that Smarter has it, in production, with links. Name concrete files, numbers and
behaviors: "the web server scales from 3 to 25 pods at 75% CPU", not "Smarter is scalable".>

- **<A feature of the code base>:** <one sentence>, with a `file link
  <https://github.com/smarter-sh/smarter/blob/main/<path>>`__.
- <four to six such bullets>

**What the course covers.** <One paragraph: the topics, in teaching order, separated by
semicolons.>

**Look at.**

- `<path> <https://github.com/smarter-sh/<repo>/tree/main/<path>>`__, <what it is>.
- <three or four entry points; the full list is in source-code.txt>

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/<docs page>`, :doc:`/adr/<NNN-name>`, <two to four pages on docs.smarter.sh>.

**Exercises.**

- <four or five open exercises, each tied to a file or commit, for instructors who build their
  own course rather than use the plans>

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <<slug>/bootcamp>
   Two-week online course: 6 hours <<slug>/two-week>
   Four-week online course: 12 hours <<slug>/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
```

## `<slug>/bootcamp.rst`

```rst
<Short Title>: Classroom Bootcamp
=================================

An eight-hour classroom bootcamp on <subject>, taught on <what in Smarter>. <Three or four
sentences: why Smarter, with two or three links, and what students do during the day.> See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course
policies, and :doc:`../<slug>` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - <who>
   * - **Deployment**
     - <a shared instance run by the instructor | Smarter from source, installed **before** the
       bootcamp>
   * - **Cost**
     - <dollars per student, and how it is capped>

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. <Verb ...>
2. ...
5. ...

Technical Prerequisites
-----------------------

- **Required:** <...>
- **Helpful:** <...>
- **Not needed:** <...>

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: <Title>.** <What it covers, naming files and commits.>
   * - 2
     - 45
     - **Lab 1: <Title>.** <What students do, in Smarter.> Produces Assignment 1.
   * - 3
     - 45
     - **Lecture 2: <Title>.** ...
   * - 4
     - 45
     - **Lab 2: <Title>.** ... Produces Assignment 2.
   * - 5
     - 45
     - **Lecture 3: <Title>.** ...
   * - 6
     - 45
     - **Lecture 4: <Title>.** ...
   * - 7
     - 45
     - **Lab 3: <Title>.** ... Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: <Title>.** ...
   * - 9
     - 45
     - **Lab 4: <Title>.** <Practice that leads into the capstone.> Ungraded.
   * - 10
     - 45
     - **Lecture 6: <Title>.** ...
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone and <first concrete step>.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: <Title>
~~~~~~~~~~~~~~~~~~~~~

<Two or three sentences: what students do, and in which files or resources.>

**Turn in:** <what, in what form>.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - <Criterion>
     - <n>
     - <full marks, in a short sentence>
     - <the commonest shortfall, in a few words>
   <three to five rows; Pts total 20>

<Assignments 2 and 3 alike.>

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: <Title>
~~~~~~~~~~~~~~~~~~~

**Learning objective.** <One sentence.>

<What students build or analyze, and in which part of Smarter.>

**What students turn in:**

- <deliverable, e.g. a pull request against their fork, a manifest, a report of n pages>
- <a presentation or an oral check>

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   <four to six rows; Pts total 100>

Capstone B: <Title>
~~~~~~~~~~~~~~~~~~~

<Same shape. A real alternative to A, not a variant of it.>

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/<docs page>`, <and one short external piece>.
- **Reference:** <Author>, *<Title>* (<edition>, <Publisher>, <year>), <why>.
- **In the repository:** `<file> <https://github.com/smarter-sh/smarter/blob/main/<path>>`__, ...

Further Study
-------------

.. include:: further-study.txt
```

## `<slug>/two-week.rst` and `<slug>/four-week.rst`

The same sections as the bootcamp, with these differences:

- Title suffix `: Two-Week Online Course` or `: Four-Week Online Course`. The
  intro paragraph says "There are <six | twelve> 30-minute recorded lectures and
  a 90-minute live session each week", and for four weeks, what each week
  covers ("Week 1 covers ..., week 2 ...").
- At a Glance adds **Workload**: "3 hours of instruction and 4 to 6 hours of
  assignments each week."
- Prerequisites may say **Required by the end of week 1:** for setup.
- The schedule table is `:widths: 10 18 72` with columns Week, Item, Content.
  Items are `Lecture N` (two-week: `Lecture N (30 min)`) and `Live session N`
  (two-week: `Live session N (90 min)`). Each week is three lectures and one
  live session. A live session row says what is demonstrated, what students
  do, which assignment is reviewed, and which is started. The last live
  session is "Capstone presentations (about <5 | 6> minutes each, with 2
  minutes of questions)", plus a course retrospective for four weeks.
- After the table, one paragraph of due dates. Two-week: "Assignment 1 is due
  at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
  and the capstone at the start of Live session 2." Four-week: "Assignments 1
  to 3 are due before the next live session. Assignment 4 is due in the middle
  of week 4. The capstone proposal is due before Live session 3, and the
  capstone at the start of Live session 4."
- Capstone intro: "Students choose one, and present it in Live session 2." or
  "Students choose one, propose it before Live session 3, and present it in
  Live session 4."
- Recommended Texts uses **Required:** bullets that name the week they're read
  in.

## `<slug>/source-code.txt`

Included into each plan under its "Smarter in the Source Code" section, so it
has no page title and starts at `~` subsections.

```rst
Every lecture, lab and assignment in this course rests on the files below. Every reference is to
the ``main`` branch of `github.com/smarter-sh/smarter <https://github.com/smarter-sh/smarter>`__,
unless another repository is named, so that students can open each one during class. Python paths
are under ``smarter/smarter/``.

<Theme 1, e.g. The Image>
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Topic
     - What Smarter does
     - Where to look
   * - <Short topic>
     - <Two to four sentences: what the code does and why, specifically enough that a student
       knows what to look for when they open it. Add :doc: links to ADRs and pages here.>
     - `<file> <https://github.com/smarter-sh/<repo>/blob/main/<path>>`__,
       `<file> <...>`__

<Three to five themes, in the order the course teaches them, five to eight rows each.>

<Optional last theme, for courses with history worth reading:>

<Topic> in the History
~~~~~~~~~~~~~~~~~~~~~~

<One sentence on what the commits show.>

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Commit
     - Why it is worth studying
     - Where to look
   * - <Short name>
     - <What was wrong, what changed, what to look for in the diff.>
     - `commit <sha9> <https://github.com/smarter-sh/smarter/commit/<sha40>>`__,
       `<file changed> <...>`__
```

## `<slug>/further-study.txt`

Included into each plan under "Further Study". Bullets only, no heading.

```rst
- **Official documentation:** `<Project> documentation <https://...>`__, <which parts>.
- **<Standards | Research | Tools | Community | Writing | ...>:** <resources>.
- **YouTube:** <channels or named talks, with speaker and year>.
- **Podcasts:** <named podcasts that cover the subject regularly>.
```
