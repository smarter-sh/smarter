Course Formats and Grading
==========================

Every micro course in this guide comes with three complete course plans: a one-day classroom
bootcamp, a two-week online course and a four-week online course. Each plan has a schedule,
graded assignments with rubrics, two capstone projects, recommended texts, further study and the
technical prerequisites. This page explains what the three formats have in common, so that the
plans themselves can stay short. An instructor should be able to take a plan, adjust the dates,
and teach it.

:doc:`Master classes </smarter-instructors/example-courses/master-classes>` are longer, and have formats of
their own. The :doc:`/smarter-instructors/example-courses/master-classes/django-master-class`, for example, has
18 hours of instruction, in eighteen one-hour modules of lecture and lab, taught as a three-day
classroom course or a six-week online course. Their plans describe their own schedules, live
sessions and grade weights, and use the rubric levels and course policies on this page.

The Three Formats
-----------------

.. list-table::
   :header-rows: 1
   :widths: 22 26 26 26

   * -
     - Classroom bootcamp
     - Two-week online course
     - Four-week online course
   * - **Instruction**
     - 8 hours
     - 6 hours
     - 12 hours
   * - **Lectures**
     - Six 45-minute lectures (4 h 30)
     - Six 30-minute recorded lectures (3 h)
     - Twelve 30-minute recorded lectures (6 h)
   * - **Hands-on time**
     - Four 45-minute guided labs and a 30-minute capstone kickoff (3 h 30)
     - Two 90-minute live sessions, one a week (3 h)
     - Four 90-minute live sessions, one a week (6 h)
   * - **Student work outside class**
     - About 6 to 10 hours, for the capstone, in the week after the bootcamp
     - About 4 to 6 hours a week
     - About 4 to 6 hours a week
   * - **Graded assignments**
     - Three lab assignments, finished in class
     - Three assignments
     - Four assignments
   * - **Capstone**
     - Due one week after the bootcamp
     - Presented in the second live session
     - Presented in the fourth live session

The bootcamp's eight hours fit one long day or two half-days. Breaks and lunch are not counted.
Each online lecture is a 30-minute recording that students watch before the week's live session.
The live session is for demonstrations, questions, pair work and reviewing assignments, not for
repeating the lectures.

Standard Bootcamp Day
~~~~~~~~~~~~~~~~~~~~~

Every bootcamp plan uses the same eleven blocks. For two half-days, split after block 5.

.. list-table::
   :header-rows: 1
   :widths: 10 15 75

   * - Block
     - Minutes
     - Purpose
   * - 1
     - 45
     - Lecture 1
   * - 2
     - 45
     - Lab 1, which produces graded assignment 1
   * - 3
     - 45
     - Lecture 2
   * - 4
     - 45
     - Lab 2, which produces graded assignment 2
   * - 5
     - 45
     - Lecture 3
   * - 6
     - 45
     - Lecture 4
   * - 7
     - 45
     - Lab 3, which produces graded assignment 3
   * - 8
     - 45
     - Lecture 5
   * - 9
     - 45
     - Lab 4, ungraded practice that leads into the capstone
   * - 10
     - 45
     - Lecture 6
   * - 11
     - 30
     - Capstone kickoff: students choose a capstone, form teams if allowed, and start work

Standard Live Session
~~~~~~~~~~~~~~~~~~~~~

Unless a plan says otherwise, each 90-minute live session runs as follows:

- **15 minutes:** questions on the week's lectures, and common problems seen in submitted work.
- **45 minutes:** a live demonstration, then pair or small group work in breakout rooms.
- **20 minutes:** the week's assignment is started together, so that nobody leaves blocked.
- **10 minutes:** a preview of next week, and an exit ticket (one thing learned, one question).

The last live session of each online course is given over to capstone presentations.

Grading
-------

Grade Weights
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 22 22 22

   * - Component
     - Bootcamp
     - Two weeks
     - Four weeks
   * - Graded assignments
     - 45% (3 × 15%)
     - 45% (3 × 15%)
     - 50% (4 × 12.5%)
   * - Participation (labs, live sessions, exit tickets)
     - 10%
     - 10%
     - 10%
   * - Capstone project
     - 45%
     - 45%
     - 40%

A final grade of 70% or more passes. Bootcamps that award a certificate of completion rather than
a grade can use the same threshold.

Reading a Rubric
~~~~~~~~~~~~~~~~

Assignments are worth 20 points and capstones 100 points. Each rubric lists its criteria and their
points, and describes two anchor levels: **Exemplary**, which earns full points, and
**Developing**, which describes the most common way of falling short. Score every criterion on
this four-level scale:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Level
     - Points
     - Meaning
   * - Exemplary
     - 100%
     - Fully meets the description in the rubric, with no significant errors.
   * - Proficient
     - 80%
     - Meets the description, with minor errors or omissions that do not affect the result.
   * - Developing
     - 50%
     - Matches the Developing description: attempted, but incomplete or partly wrong.
   * - Missing
     - 0%
     - Not attempted, or does not work at all.

Course Policies
---------------

Adapt these to your institution's rules, and state them on the first day.

- **Late work.** Online assignments lose 10% for each day late, up to three days, after which they
  are not accepted. Bootcamp lab assignments are finished in class. The bootcamp capstone may be
  submitted up to three days late for a 10% penalty.
- **Use of AI assistants.** Students may use AI assistants, including coding agents, unless an
  assignment says otherwise, and must say how they used them in a short note with each
  submission. They are graded on their understanding, so expect to be asked to explain any line
  that they turn in. The :doc:`agentic-development` course takes this further.
- **Evidence of process.** Smarter's :doc:`journal </smarter-platform/smarter-journal>` records
  every prompt and tool call, so prompt engineering and AI application assignments can ask for
  the conversation that produced a result. Tell students that their prompts are recorded.
- **Submissions.** Manifests, code, documents and design notes are submitted in a Git repository,
  one per student or team, with a tag or pull request for each assignment. Slides and videos are
  linked from the repository's ``README.md``.
- **Teams.** Capstones may be done alone or in teams of two or three, unless a plan says
  otherwise. A team states who did what in its ``README.md``, and each member presents.
- **Personal data.** Exercises use invented names and records only.

Before Teaching a Plan
----------------------

- Work through every lab and assignment yourself on the same installation that your students will
  use, and time it.
- Set up accounts, API keys and a :doc:`Budget </smarter-resources/smarter-budget>` for each
  student, as described in the :doc:`Smarter Instructor Guide </smarter-instructor>`.
- Send the technical prerequisites and the installation instructions to students at least a week
  ahead. For a bootcamp, ask students to prove their installation works, with a screenshot,
  before they arrive: there is no time to fix laptops on the day.
- Record the online lectures ahead of time. A screen recording of the web console, a terminal and
  the documentation, with a few slides, is enough.
- Check that the recommended books are available to students, through your library or a
  subscription such as O'Reilly Learning, and substitute where they are not.
