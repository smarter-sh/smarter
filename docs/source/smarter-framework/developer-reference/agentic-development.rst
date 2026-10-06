Agentic Development
===================

Smarter has reached a kind of critical mass in its use of agentic AI. Nearly all
new code is now designed, written and tested by coding agents such as Claude
Code, working from the existing code base and the
`Agent Skills <https://github.com/smarter-sh/smarter/tree/main/skills>`_ in the
repository's ``skills/`` folder.

Skills are one of several things that decide how well an agent works on this
repository. But the lion's share of the impact stems from characteristics of the
code base itself, and of how you interact with the agent. The points below come
from building Smarter with agents. They're observations, not hard rules.

How You Ask
-----------

- **Ask for outcomes, not steps.** Agents do their best work on broad,
  well-bounded requests, such as "add a new resource kind for X, with tests,
  docs and a console list page", rather than step-by-step instructions. A broad
  request lets the agent follow the code base's existing patterns from end to
  end and check its own work as it goes. Narrow, surgical requests often go
  less well, usually not because the problem is small but because the agent
  can't see what you see: the failing behavior, the log line, the state of
  production.
- **When the problem is narrow, give the agent the evidence.** Paste the stack
  trace, the failing request or the steps to reproduce it. Better still, ask
  for a failing test first. An agent that can reproduce a bug can usually fix
  it. One that can't will guess.
- **Say what "done" means.** State the acceptance criteria and constraints up
  front: which tests must pass, what mustn't change, whether a migration is
  allowed, what needs documenting. An unstated constraint is the most common
  reason a correct-looking change has to be redone.
- **Point at an example.** "Do it the way ``smarter-plugin-list`` does it" is
  worth several paragraphs of description.
- **Plan large changes before writing them.** For work that spans several
  apps, ask for a plan first (Claude Code has a plan mode for this), correct
  it, and then let the agent implement it. A plan is cheaper to fix than a
  diff.
- **Start a fresh session for each task.** A long session carries stale context
  from earlier work, and the agent's attention is spread across all of it.
- **Turn repeated corrections into skills.** If you've corrected an agent on
  the same point twice, the correction belongs in a skill. The
  `skills README <https://github.com/smarter-sh/smarter/tree/main/skills#readme>`_
  explains when and how to add one.

What the Code Base Gives the Agent
----------------------------------

Mind you, arriving at a code base that is ideally suited towards agentic
AI was an iterative process that was years in the making. Looking backwards,
these are the characteristics of the Smarter codebase that seem to have led to
the most positive impact.

- **Existing, similar code.** Agents are very good at following a pattern. If
  the code base already has three of something, the agent usually gets the
  fourth right the first time. Something with no precedent is where agents make
  the most design mistakes, so build the first one carefully, and treat it as
  the template for the rest. For example, Smarter's Django apps follow a
  deliberately rigid structure for this very reason. Additionally, building
  on top of an opinionated framework like Django helps, a lot.
- **One way of doing each thing.** Consistency matters as much as quality. When
  two patterns coexist, such as an old and a new base class, the agent may copy
  whichever it finds first. Finish migrations to a new pattern, delete dead
  code, and mark anything legacy as legacy. Smarter deliberately takes a
  conformist approach: Python code should be Pythonic, and Django code should
  follow the practices of the Django community. There exists a force multiplier
  in keeping your code DRY, in that it leads to a clearer set of instructions
  for AI agents.
- **A thorough test suite.** Tests are how an agent learns whether its change
  works and what it broke. Good coverage lets it make sweeping changes safely.
  Poor coverage means it reports success it hasn't verified. Watch for an agent
  that "fixes" a failing test by weakening the test instead of the code. See
  :doc:`devops/test`.
- **A fast feedback loop the agent can run itself.** Tests, linters, type
  checks and builds that run locally in seconds or minutes get run after every
  change. Ones that take 30 or 40 minutes, or need a person to click something,
  don't. That's why the ``smarter-sphinx-docs`` skill describes a quick check
  instead of the full Sphinx build. Smarter has more than 5,000 unit tests
  which take upwards of a half hour to run locally. Thus, it behooves you to
  help an agent find way to work smarter.
- **Well-defined CI/CD.** A pipeline that builds, tests and deploys the same
  way every time is a final, impartial check on the agent's work, and its
  ``make`` targets and scripts give the agent commands to run instead of
  reconstructing them. See :doc:`devops/ci-cd`.
- **Well-known frameworks, used conventionally.** Agents have seen a great deal
  of Django, React, Pydantic and Kubernetes code and know their idioms. A
  custom framework, or an unusual use of a popular one, has to be relearned
  from your code in every session. Explaining those is what skills such as
  ``smarter-sam-resource`` are for.
- **Clean, consistently formatted code.** Code that has passed formatters,
  linters and security scanners makes a better example. Agents copy what they
  see, including unused imports, mixed styles and suppressed warnings. The same
  pre-commit hooks also catch the agent's own mistakes before you review them.
- **Types and schemas.** Type hints and Pydantic models state contracts the
  agent would otherwise have to infer, and turn a wrong guess into an immediate
  error. For this reason, Smarter vigorously enforces type annotations and strong
  type checking throughout the entire codebase.
- **Names you can search for.** An agent explores a code base mostly with text
  search and file listings. Specific, unambiguous, distinctive names for files, classes and
  settings make the right code easy to find. Generic ones (``utils.py``,
  ``helpers``, ``Manager``) make the wrong code easy to find.
- **Useful error messages and logs.** An agent debugs from what the code
  prints. An error that names the value, what was expected and where saves
  several rounds of guessing. A great deal of effort has gone into what Smarter
  logs, and exactly what information is included in each log message.
  For example, each log entry begins with the dotted path of the code that wrote it,
  such as ``smarter.apps.account.models.account.Account.get_cached_object()``.
  Moreover, logging is controlled by :doc:`waffle switches </adr/022-feature-flags>`
  and curated for development, so that an agent has the information it needs
  in order to accurately follow a thread of execution. See :doc:`lib/logging`.
- **Accurate and complete docs.** Agents believe what they read. A stale
  comment or docstring is worse than none. Smarter's Sphinx documentation is
  written as much for agents as for people, so that they fully understand
  the intent behind a piece of code, and the broader context in which
  it operates. As of version v0.14 Smarter has more than 1,000 pages of consistently
  formatted technical documentation, published to `docs.smarter.sh <https://docs.smarter.sh/>`_.
  Keep in mind that agentic AI is able to search and browse this information
  in the same way as humans. This has a huge impact on the effectiveness of agentic AI.
- **A safe place to experiment.** Agents work best when they can run things
  freely. Every live credential or irreversible side effect in the development
  environment means either constant confirmation prompts or a risk of real
  damage. Fakes, guards and sandboxes, as described in the
  ``smarter-infrastructure-safety`` skill, let you safely give the agent more
  autonomy.
- **Written-down tribal knowledge.** Anything a new developer would have to be
  told, such as setup steps, gotchas and the reasons behind conventions, an
  agent has to be told in every session. That's what the ``skills/`` folder is
  for.

Reviewing What You Get
----------------------

- **Review the diff as you would a colleague's.** An agent sounds just as
  confident when it's wrong. Look especially for changes outside the scope of
  the request, edited or deleted tests, new ``# noqa`` or ``# nosec`` comments,
  and new dependencies.
- **Keep changes reviewable.** A broad request is fine, but ask for the result
  in pieces you can actually review, such as one pull request per app or layer.

Most of these properties make a code base easier for people to work on, too. An
agent just exposes their absence faster.
