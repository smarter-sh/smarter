Open Source Participation
=========================

**Why Smarter.** Open source is usually taught by pointing students at a huge project, where a
newcomer's pull request can wait months, or at a toy repository that nobody else uses. Smarter is
in between: a real platform in production, developed entirely in public, small enough that a
contribution is noticed, and run with the same practices as much larger projects:

- **A clear license.** The `AGPL-3.0 <https://github.com/smarter-sh/smarter/blob/main/LICENSE>`__,
  whose network clause makes it a good case study: it applies when a modified version is offered
  to users as a service, not only when it is distributed.
- **Published rules.** A `contributing guide
  <https://github.com/smarter-sh/smarter/blob/main/CONTRIBUTING.md>`__, a `code of conduct
  <https://github.com/smarter-sh/smarter/blob/main/CODE_OF_CONDUCT.md>`__, a `security policy
  <https://github.com/smarter-sh/smarter/blob/main/SECURITY.md>`__ for private vulnerability
  reports, issue forms, a `pull request template
  <https://github.com/smarter-sh/smarter/blob/main/.github/PULL_REQUEST_TEMPLATE.md>`__ and a
  `CODEOWNERS <https://github.com/smarter-sh/smarter/blob/main/.github/CODEOWNERS>`__ file.
- **Automation that teaches the workflow.** Every commit message is checked by
  `commitlint <https://github.com/smarter-sh/smarter/blob/main/commitlint.config.js>`__, the
  `pre-commit hooks <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml>`__
  check formatting, spelling, security and secrets, and
  `semantic-release <https://github.com/smarter-sh/smarter/blob/main/release.config.js>`__ turns
  conventional commits into versions and `changelogs
  <https://github.com/smarter-sh/smarter/tree/main/changelogs>`__ on four release branches. The
  project has published more than five hundred releases.
- **Many ways in.** Issues, `discussions <https://github.com/smarter-sh/smarter/discussions>`__
  and `pull requests <https://github.com/smarter-sh/smarter/pulls>`__ in the main repository; more
  than nine hundred pages of documentation; and smaller repositories in the
  `smarter-sh <https://github.com/smarter-sh>`__ organization, such as the Go CLI, the chat
  component, the VS Code extension and the Python SDK, where a first contribution is easier.
- **A project whose health students can measure.** Twenty-two contributors, one code owner, and a
  public history of every release, so the bus factor, governance and sustainability are concrete,
  and a class's contributions make a visible difference.

A course or a capstone can end with a real contribution to a real project. A merged pull request
is a public, verifiable piece of work for a student's portfolio.

**What the course covers.** How open source works: motivations, roles, governance and funding;
copyright, permissive and copyleft licenses, the AGPL and compatibility; reading a project's rules;
the pull request workflow: forks, branches, conventional commits, hooks, CI and semantic
versioning; documentation contributions in reStructuredText; choosing a substantial issue and
asking first; code contributions that follow a project's patterns; giving and receiving code
review; coordinated disclosure, CVEs and supply chain security; project health, CHAOSS metrics and
the bus factor; and sustaining contribution, from triage to becoming a maintainer.

**Look at.**

- The project's `issues <https://github.com/smarter-sh/smarter/issues>`__, by
  `label <https://github.com/smarter-sh/smarter/labels>`__, and its
  `pull requests <https://github.com/smarter-sh/smarter/pulls>`__.
- `CONTRIBUTING.md <https://github.com/smarter-sh/smarter/blob/main/CONTRIBUTING.md>`__,
  `SECURITY.md <https://github.com/smarter-sh/smarter/blob/main/SECURITY.md>`__ and
  `release.config.js <https://github.com/smarter-sh/smarter/blob/main/release.config.js>`__.
- The `releases <https://github.com/smarter-sh/smarter/releases>`__ and the
  `CHANGELOG.md <https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG.md>`__ they produce.

Each course plan lists every file and page that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/guides/contributing`,
:doc:`/smarter-framework/guides/code-of-conduct`,
:doc:`/smarter-framework/guides/developer-guidelines`,
:doc:`/smarter-framework/guides/semantic-versioning`,
:doc:`/smarter-framework/guides/documentation`.

**Exercises.**

- Choose an issue, discuss the approach with the maintainers in the issue before writing code,
  and see a pull request through review.
- Improve the documentation: a clearer explanation, a missing example, or a corrected command.
  This is the easiest first contribution, and one of the most valued.
- Read the AGPL-3.0 license, and explain what it allows and requires, and how it differs from the
  MIT and Apache licenses.
- Follow one feature from its conventional commit to the release and the changelog entry that
  semantic-release produced from it.

.. note::

   Contact the maintainers in `GitHub Discussions <https://github.com/smarter-sh/smarter/discussions>`__
   before a large class starts contributing, so that they can label suitable issues as
   ``good first issue`` and plan for the reviews.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <open-source/bootcamp>
   Two-week online course: 6 hours <open-source/two-week>
   Four-week online course: 12 hours <open-source/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
