Shadow AI: Taking Control of the AI Projects Already Running
============================================================

*Before Stackademy installed Smarter, its departments had already built AI projects of their own. No one knew how
many there were, what they did, which AI services they called, or what company data went out with each call. Smarter
put every project behind one gateway without stopping any of them, and then made the leaky ones safe, and cheaper.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy, an online code academy of 40 employees in seven departments, whose records, from payroll to the
       general ledger, are in one MariaDB database.
   * - Problem
     - Several departments had built their own AI projects, each with its own API key for a third-party AI service.
       Spending on AI services grew every month of 2025, and ended the year 27% over budget. No one could say how
       many projects there were, what each was for, which services they called, or whether private data was being
       sent to those services. Some of it was.
   * - Solution
     - Phase 1: a Smarter **Proxy** for each project, a drop-in replacement for the AI service it called, with a
       Smarter API key of its own, so that every project keeps running and every call goes through Smarter. Phase 2:
       the projects that sent private data or company know-how out were rebuilt as LLMClients with **SqlPlugins**,
       **ApiPlugins** and an **MCPClient**, which send the AI model the few rows a question needs, instead of whole
       tables. The first was the website's course chatbot, which became Stanley (:doc:`ask-stanley`).
   * - Smarter features
     - Proxy; Secret; Smarter API keys; Budget; cost accounting; LLMClient; SqlPlugin; ApiPlugin; MCPClient; Guardrail.
   * - Outcome
     - Seven projects found, each with an owner, a purpose and a budget. No AI provider key outside Smarter. Every
       call attributed to a project and a person. Five projects rebuilt: three no longer send private records out,
       and two no longer send Stackademy's course designs. Their prompts are a small fraction of their former size.

Executive summary
-----------------

AI arrived at Stackademy the way it arrives at most companies: department by department, before anyone set a policy.
An accountant wrote a notebook that drafts the month-end commentary. Admissions wired a model into its follow-up
emails. HR scripted a résumé screener. Each was a good idea, built quickly by someone who needed it to get their work
done faster, with an API key pasted into a script. The will to build was already there. What was missing was a place
to build well, under the company's rules. By the end of 2025, Stackademy paid an AI services vendor more each month
than the month before, $51,264 for the year against a budget of $40,400, and IT, which paid the bill, could not say
what it paid for.

The questions that mattered were basic, and no one could answer them. How many AI projects are there? What does each
one do, and for whom? Which providers do they call, with whose keys? And the one that kept the Chief Financial
Officer awake: **is our private data, salaries, students' records, the general ledger, being sent to those
providers?**

Stackademy answered them in two phases. In the first, it installed Smarter and gave each project a **Proxy**: a URL on
Smarter that behaves exactly like the AI provider's API, so that the project's only change was two lines, its base URL
and its API key. The provider keys moved into Smarter, as Secrets, and each project got a Smarter API key of its own.
From then on, every call that any project made went through Smarter, which attributes its tokens to the project and
the person, stops it at the project's budget, and refuses anything but the endpoints the project needs. Nothing
stopped working. A seventh project, which no one had listed, revealed itself the day the old keys were revoked.

The first phase also showed which projects were dangerous: five of them sent prompts of thousands, or tens of
thousands, of tokens, because they pasted whole tables or document sets into every prompt and let the model find the
answer. In the second phase, those five were rebuilt as Smarter LLMClients whose tools fetch only what a question
needs: **SqlPlugins** over each department's read-only database user, an **ApiPlugin** over the course catalogue's
API, and an **MCPClient** over the course repository. The first was the course chatbot on Stackademy's website, which
became **Stanley**, the assistant that :doc:`ask-stanley` describes. Private records and course designs stay in the
database; the model sees a few rows; and each prompt costs a fraction of what it did.

Background
----------

Stackademy is an online code academy, with 48 courses in programming, cloud and AI, about $4.4 million of revenue in
its fiscal year 2025, and 40 employees in seven departments. Its IT department is its Head of IT, Tomas Hartigan, and
two engineers. The rest of its people are accountants, recruiters, instructional designers and advisors, a few of whom
write Python.

Stackademy's own books record what AI cost it. Its general ledger has an expense account for it, **5300 AI Services**,
and one vendor, Cortex AI Services, invoices it every month, charged to IT:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - 2025, account 5300 AI Services
     - Actual
     - Budget
   * - January
     - $2,688.00
     -
   * - June
     - $4,128.00
     -
   * - December
     - $5,856.00
     -
   * - **The year**
     - **$51,263.98**
     - **$40,400.00**

The invoice grew by $288 every month, and more than doubled over the year. The budget, set at the
start of the year, didn't foresee it. And the invoice is one line a month: it says how much, not who, what, or why.
Beside it, the ``expense_reports`` table holds 20 reports in the category *Software*, $2,988.92 from 17 employees,
which don't say what was bought.

The people
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 26 22 30

   * - Person
     - Title
     - Department
     - Their part in this case
   * - Odette Hartigan
     - Chief Financial Officer
     - Finance and Accounting
     - Wants to know what the AI invoice pays for, and to cap it
   * - Tomas Hartigan
     - Head of IT
     - Information Technology
     - Pays the invoice; owns the provider keys, Smarter and the migration
   * - Kofi Sandoval
     - Staff Accountant
     - Finance and Accounting
     - Wrote the month-end commentary notebook
   * - Avery Ivanova
     - HR Director
     - Human Resources
     - Owns the résumé screener, which a contractor wrote
   * - Dmitri Dumont
     - Admissions Director
     - Admissions and Sales
     - Owns the website's course chatbot and the enrollment follow-up emails
   * - Odette Eriksen
     - Head of Course Content
     - Course Content
     - Owns the lesson reviewer

The Stackademy people, accounts and database in this case are the real resources of
`smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__, and the figures above are what its database
returns. The seven legacy projects are not in that repository: they are the situation this case starts from, which
any organization that adopts an AI platform late will recognize. Everything that Smarter does in it is real, and
documented in the pages that `Sources`_ lists.

The challenge
-------------

What leaving it there costs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Shadow AI, the AI that people build and run outside any platform, is not a discipline problem: it is evidence that
people want AI in their work, and that the official path to it is too slow. But left where it is, it costs the
business in four ways:

- **Visibility.** No one can say what AI is in use, what it costs, or what it returns. Stackademy's leadership saw
  one invoice line a month.
- **Data.** What a project sends to an AI provider is decided by whoever wrote it, and reviewed by no one.
- **Reuse.** What one person builds alone can't be shared, reused or scaled. Kofi's notebook runs on Kofi's laptop,
  with Kofi's key; no one else in Accounting can run it.
- **Continuity.** When the person who built it leaves, the solution leaves with them, or, worse, keeps running with
  no one who knows it is there.

The requirements
~~~~~~~~~~~~~~~~

Stackademy's leadership set five requirements:

1. **Inventory.** Find every AI project: what it does, who owns it, which provider and model it calls, how often, and
   at what cost.
2. **No outage.** The projects are in daily use. Admissions' emails go out every night; Accounting's commentary is due
   at every month-end. None may stop while it is brought under control.
3. **One place for keys.** No AI provider key in a script, a notebook, a CI variable or a laptop. A key must be
   revocable, per project, without breaking the others.
4. **Bounded and attributed spending.** Each project's tokens counted, charged to its department, and stopped at a
   limit.
5. **No private data sent where it needn't go.** Where a project sends salaries, students' records, the ledger or
   Stackademy's course designs to an AI provider, change the project so that it doesn't.

The first four are about control, and must hold from the first day. The fifth is about design, and takes longer: it
means changing how a project works, not only where it sends its calls.

Options considered
------------------

There are three ways to respond to shadow AI: ignore it, ban it, or enable it.

.. figure:: /_static/case-studies/shadow-ai-responses.svg
   :alt: Three cards. 1, Ignore it: everyone keeps building alone, nothing is shared, and no one sees it; at
         Stackademy, the AI invoice grows $288 a month and data leaves unseen. 2, Ban it: some people stop, others go
         around the rule, and the business slows down; at Stackademy, the month-end commentary, the nightly emails and
         the screener stop, and the rest hide. 3, Enable it, the one chosen: one place to build and run AI, under the
         company's rules, with nothing rewritten on day one; at Stackademy, a Proxy per project at once, and the leaky
         ones rebuilt next.
   :width: 100%

   Exhibit 1. Three ways to respond. The third makes the easy path the governed one.

Each has more than one form:

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - **Ignore it**, or answer it with a policy: register your AI projects, and stop sending private data
     - Cheap; states the expectation
     - Relies on the people who didn't know there was a problem; finds only the projects their owners remember; checks
       nothing. The invoice keeps growing
   * - **Ban it**: shut down every unapproved project, and rebuild the useful ones
     - A clean start
     - Breaks the month-end, the nightly emails and the screener at once; costs the goodwill of the people who built
       them; the rebuild queue is IT's two engineers; the projects that matter most move to personal accounts, where
       no one sees them
   * - **Ban it** at the network: filter the providers' domains
     - Sees calls from the office network
     - Doesn't see laptops at home or hosted notebooks; sees that a call was made, not by which project; enforces no
       budget
   * - Rotate the provider keys, and see what breaks
     - Finds every project that uses a known key, quickly
     - Finds them by breaking them; leaves each one to find its own new key, scattered as before
   * - **Enable it: a Smarter Proxy per project, then a rebuild of the leaky ones** (chosen)
     - Two lines changed per project; no outage; keys, budgets and attribution from day one; the rebuild can wait for
       the inventory to say which projects need it; the people who built the projects keep them, and help
     - The Proxy forwards prompts as they are, so in phase 1 private data still goes out until the project is rebuilt;
       it needs each owner to change their project once

Stackademy did use the key rotation, but last, as a check rather than as the plan: once every known project had moved
to its Proxy, the old provider keys were revoked, and anything still using them would show itself.

The solution
------------

Phase 1: a Proxy for every project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Smarter **Proxy** gives passthrough access to an AI provider's API. A project calls it with the provider's own SDK,
unchanged, as if it were the provider: the same paths, the same request bodies, the same responses, including
streams. Two things differ. The project's base URL is the Proxy's, and its API key is a **Smarter API key**, not the
provider's. Smarter checks the Smarter key, adds the provider's key from a Secret, forwards the request, and returns
the provider's response as it is.

For Kofi Sandoval's month-end notebook, the whole change was this:

.. code-block:: python

   # Before: the provider's key, from the notebook's environment
   client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

   # After: the project's Proxy on Stackademy's Smarter platform, and the project's Smarter API key
   client = OpenAI(
       base_url="https://smarter.stackademy.example/api/v1/proxy/accounting_month_end_commentary/",
       api_key=os.environ["SMARTER_API_KEY"],
   )

The Anthropic and Google Gen AI SDKs change the same way, with their ``base_url``; Smarter reads its API key from the
header each SDK sends it in, ``x-api-key`` for Anthropic and ``x-goog-api-key`` for Gemini.

.. figure:: /_static/case-studies/shadow-ai-proxy.svg
   :alt: Before, seven projects called three providers directly, with provider keys in scripts, notebooks, a
         spreadsheet and a CI variable, and one invoice a month, charged to IT. After, each project, the website's course
         chatbot, the month-end commentary, the résumé screener, the enrollment follow-up, the lesson reviewer, the
         helpdesk bot and the ad copy drafter,
         calls Smarter with its own Smarter API key. Inside Smarter, in the project's department account, are its
         Smarter API key, one per project, revocable, with its last use; its Proxy, with allowedPaths such as
         chat/completions; the department's Budget, which answers 402 at the limit; the Secret that holds the
         provider's key, which never leaves; and the charges, tokens by project, person and model. Smarter adds the
         provider's key and forwards each call to OpenAI, Anthropic or Google Gemini.
   :width: 100%

   Exhibit 2. Phase 1. Each project changes two lines, and from its first call has an owner, a key, a budget and
   its own charges.

Each project got its own Proxy, in its department's account, declared in a manifest that IT reviewed:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     name: accounting_month_end_commentary
     description: Accounting's month-end commentary notebook. Owner, Kofi Sandoval.
     version: 1.0.0
   spec:
     provider: openai
     apiKey: stackademy_accounting_openai_api_key   # a Secret of the Accounting account
     baseUrl: https://api.openai.com/v1/
     allowedPaths:
       - chat/completions
     timeout: 300
     isActive: true

Every account may use Smarter's built-in Proxies, such as ``openai``, which would have worked as well. Stackademy gave
each project its own instead, for three reasons: each Proxy is a line in the inventory, with a name, a description and
an owner; each has its own charges and its own budget, so a project's spending is its own; and each allows only the
paths that its project uses, here ``chat/completions``, so a Smarter API key that leaks can't upload files, start
fine-tuning jobs or read the provider account's settings.

One project, one key
~~~~~~~~~~~~~~~~~~~~

Each project's owner, as their department's administrator, was issued a Smarter API key named after the project, for
example ``accounting_month_end_commentary``, with a description that says what it is for. The key replaced the
provider key in the project's environment. That gives each project a credential that Stackademy can account for:

- **Revocable on its own.** Deactivating a key stops one project, and only that one, and can be undone.
- **Traceable.** Each key records when it was last used. A key that hasn't been used in a month is a project that
  may no longer exist.
- **Worthless outside Smarter.** A Smarter API key that leaks can call the Proxies its owner may use, at their allowed
  paths, within their budgets, and nothing else. The provider keys, which can do anything the provider account
  allows, are now in Smarter, as Secrets, which no project, log or manifest reveals. Tomas's team rotates them in one
  place.

Spending: attributed, and capped
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For every response it forwards, Smarter reads the token usage that the provider reports, including from a stream as
it ends, and records it as a charge to the Proxy, to the caller, and to the caller's account. So each project's
tokens, and their cost, are on the console's **Budgets** page and its dashboard's **Budget vs Actual** chart, by
project, by person and by department.

Each department already had a monthly AI budget for its assistant (:doc:`confidential-by-construction` describes
them). Its projects' Proxies joined it:

.. code-block:: yaml

   # budgets/stackademy-accounting-ai.yaml (abridged): the department's budget, now with its project's Proxy
   apiVersion: smarter.sh/v1
   kind: Budget
   metadata:
     name: stackademy_accounting_ai
   spec:
     config:
       unit: cost
       period: month
       periodicLimit: 150.0
       action: block
       warningThreshold: 80
     resources:
       - kind: LLMClient
         name: stackademy_accounting_assistant
         accountNumber: 2718-2818-0003
       - kind: Proxy
         name: accounting_month_end_commentary
         accountNumber: 2718-2818-0003

At 80% of the month's limit, the department is warned. At the limit, its Proxies answer ``402 Payment Required``,
in the error shape that the OpenAI and Anthropic SDKs already report, and the CFO decides whether to raise it.

The inventory
~~~~~~~~~~~~~

Tomas's team asked each department head for their projects, searched Stackademy's repositories and website for the
providers' SDKs and for strings shaped like provider keys, and matched what they found against the expense reports.
Six projects were declared. Each was moved to its Proxy, one at a time, with its owner. Then the old provider keys were
revoked, and the next morning one more project failed: a Google Sheets script that a former contractor had written
for Admissions, which drafts course descriptions for ads. No one had listed it, because no one remembered it was
there. It got a Proxy and an owner too.

After a month of traffic through the Proxies, the inventory looked like this:

.. list-table::
   :header-rows: 1
   :widths: 24 14 12 26 24

   * - Project
     - Department
     - Provider
     - What it sent
     - Finding
   * - Course chatbot, on the website
     - Admissions
     - OpenAI
     - The course brochures, and an export of every course's modules and lessons, with every question
     - **Proprietary**: all 48 course designs; out of date
   * - Month-end commentary, a notebook
     - Accounting
     - OpenAI
     - The month's full general ledger export, every run
     - **Private**; very large prompts
   * - Résumé screener, a script
     - HR
     - OpenAI
     - Each résumé, with the compensation table "for context on pay"
     - **Private**: every employee's salary
   * - Enrollment follow-up, a nightly job
     - Admissions
     - Anthropic
     - The catalogue, and an export of students and their enrollments, for each email
     - **Private**: every student's record, in every prompt
   * - Lesson reviewer, a script
     - Course Content
     - Google Gemini
     - Whole course folders, including unreleased courses
     - Company material; very large prompts
   * - Helpdesk bot, in chat
     - IT
     - OpenAI
     - Employees' IT tickets
     - Acceptable; stays on its Proxy
   * - Ad copy drafter, a spreadsheet script
     - Admissions
     - OpenAI
     - Public course names and descriptions
     - Found by the key rotation; acceptable

A Proxy doesn't keep the prompts it forwards, by design: it is a passthrough, and storing every prompt would make
Smarter a second copy of whatever a project sends. What it does keep is enough to know where to look. Each charge
records the project, the caller, the model and the tokens, and four Proxies stood out at once: the month-end
notebook averaged prompts of about 90,000 tokens, the follow-up job about 35,000 for a three-paragraph email, the
lesson reviewer more than 100,000, and the website chatbot more than 10,000 for a one-line question about a course. A
prompt that large is a prompt with a dataset in it. Reading those projects' code found what was in the datasets, and
the HR screener, whose prompts were smaller, was found by the same reading, because it was on the list.

Phase 2: rebuild what sends too much
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The five projects that stood out all made the same design choice: give the model all the data, and let it find the
answer. Their builders called it RAG, retrieval-augmented generation, but nothing was retrieved: the whole dataset
went with every prompt. It is the quickest thing to build, and it is a leak by construction.
Every prompt sends the whole table to the provider, whatever the question; it costs tokens in proportion to the size
of the table, not of the answer; and it gets slower and dearer as the table grows.

Each was rebuilt as an LLMClient in its department's account, whose tools fetch only what a question needs. The
model asks for a tool to be run, with the values it chooses; Smarter runs it; and the model gets back a few rows, not
the table.

**Admissions' course chatbot**, rebuilt with a **SqlPlugin**, went first: it was public, it was the simplest, and
its two faults were plain to see. Its knowledge was a copy of the course brochures and the course outlines that its
developer had at hand when it was built, so it could not keep up with the catalogue: it didn't know the newest
courses, and quoted prices that had changed. And every question, from anyone on the internet, sent the AI provider all
48 courses with their 176 modules and 528 lessons, which are Stackademy's course designs, its know-how, including
courses not yet released. It became **Stanley**, an LLMClient whose one tool, the SqlPlugin ``stackademy_sql``, runs a
reviewed query over the live ``courses`` table, and returns at most ten rows that match the student's question: a
course's code, name, short description, price and prerequisite, and nothing about how it is taught.
:doc:`ask-stanley` tells the rebuild in full. It proved the pattern that the four others followed.

**Accounting's month-end commentary**, rebuilt with **SqlPlugins**. Kofi's notebook asked one question of the whole
ledger: *what changed this month, and why?* Accounting's assistant, Ledger, already answers it from three reviewed
queries over the Accounting database user: ``stackademy_accounting_results`` (revenue, expenses and net income for a
period, totalled by the database), ``stackademy_accounting_income_statement`` (by ledger account) and
``stackademy_accounting_budget_vs_actual``. The model now gets a few dozen totals instead of 2,502 ledger lines.
The notebook stayed, as Kofi's tool for formatting the commentary; it now asks Ledger, through Smarter, instead of
sending the ledger to a provider. And because Ledger is an assistant in Accounting's account, not a notebook on
Kofi's laptop, the rest of Accounting can ask it too.

.. figure:: /_static/case-studies/shadow-ai-tools.svg
   :alt: Before, paste the ledger: the notebook's prompt, through its Proxy, is "Write the month-end commentary"
         followed by the 2,502 lines of gl_entries as CSV, about 88,000 tokens every run, which leave the company,
         whatever the question. After, ask Ledger, Accounting's LLMClient with SqlPlugins: the model asks for the tool
         stackademy_accounting_results for the fourth quarter of 2025; Smarter runs the reviewed query as Accounting's
         read-only database user; three totals come back, revenue, expenses and net income. The ledger stays in the
         database, and Ledger's guardrail, budget and chat history apply to every question. The same pattern rebuilt
         the others: the live courses table instead of every course design, for Stanley; HR's requisitions instead
         of every salary; one student's records instead of 320; a read-only GitHub MCPClient instead of whole course
         folders.
   :width: 100%

   Exhibit 3. Phase 2. The model gets the rows a question needs, from a reviewed query, and never the table.

**HR's résumé screener**, rebuilt with a **SqlPlugin**. The screener needs to know the position's salary range, not
everyone's salary. ``stackademy_hr_requisitions`` returns the open positions, with their salary range and applicants,
over HR's database user. The compensation table no longer leaves the database. The résumés themselves still go to the
model, because reading them is the screener's job, and HR decided, with the CFO, that this is a use the company's
provider agreement allows. A résumé goes through IT's ``stackademy_pii_redaction`` guardrail first, which removes
social security and card numbers that candidates sometimes include.

**Admissions' enrollment follow-up**, rebuilt with a **SqlPlugin** and an **ApiPlugin**. Each email is about one
student and their courses. ``stackademy_admissions_enrollments`` returns enrollments and tuition by course, over the
Admissions database user, and the ApiPlugin ``stackademy_api`` reads the course catalogue through its REST API, by
subject and price, as Stanley does in :doc:`ask-stanley`. The prompt no longer holds 320 students' records to write to
one of them.

**Course Content's lesson reviewer**, rebuilt with an **MCPClient**. The reviewer sent whole course folders, unreleased
courses among them, to check one lesson. Course Content's lessons are in a private GitHub repository, so the rebuilt
reviewer reaches it through an MCPClient over GitHub's MCP server, limited to read-only tools, with a read-only token
that a Secret holds:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: MCPClient
   metadata:
     name: content_course_repository
     description: Course Content's lessons, read-only, for the lesson reviewer.
     version: 1.0.0
   spec:
     config:
       transport: http
       endpointUrl: https://api.githubcopilot.com/mcp/
       authType: bearer_token
       credentials: stackademy_content_github_read_token   # a Secret: a read-only token for one repository
       allowedTools:
         - get_*
         - search_*
       includeInstructions: true
       isActive: true

The model now searches the repository and reads the files the lesson refers to, and nothing else. A write tool, such
as one that opens a pull request or pushes a file, is not offered to it.

The two phases, side by side
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * -
     - Phase 1: Proxy
     - Phase 2: LLMClient with tools
   * - What changes in the project
     - Its base URL and its API key
     - How it gets its data: tools, not pasted tables
   * - Who does it
     - The project's owner, in an hour
     - The owner and IT, a project at a time
   * - Keys, attribution, budget, allowed paths
     - Yes, from the first call
     - Yes
   * - What reaches the AI provider
     - Whatever the project sends, as before
     - The question, and the rows its tools return
   * - Guardrails
     - No: the Proxy forwards requests as they are
     - Yes, the LLMClient's
   * - Record of each call
     - Who, which project, which model, how many tokens; not the prompt
     - The conversation, each tool call and its results, in the LLMClient's chat history
   * - Use it for
     - Every project, at once; and for good, for projects that send nothing private
     - The projects whose prompts carry private data or whole datasets

Implementation
--------------

The order mattered more than the technology.

1. **Smarter first, with the provider keys.** Tomas's team installed Smarter, set up Stackademy's accounts (see
   :doc:`organizing-for-ai`), and stored the company's provider keys as Secrets in each department's account. A Proxy
   may send only a Secret of its own account, so a department's Proxies can't use another department's key, or the
   platform's.
2. **A Proxy and a key per project, one project at a time.** Each owner changed two lines, ran the project once, and
   checked its answer was the same. The Proxy's response carries an ``X-Smarter-Proxy`` header with the Proxy's name,
   which shows the call went through Smarter.
3. **Budgets.** Each project's Proxy joined its department's Budget.
4. **Revoke the old keys.** Only after every declared project had moved, so that whatever broke was undeclared.
5. **Measure, then rebuild.** A month of charges, read by project, ranked the rebuilds by prompt size and by what the
   prompts held. The website's course chatbot went first, as the pilot, because it was public and its data was the
   simplest; the three projects that sent private records followed, and the lesson reviewer last.

Phase 1 took about two weeks, most of it waiting for owners. Each rebuild in phase 2 took a few days, much of it
deciding what the project really needed from the data.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Before → after
   * - AI projects known to IT
     - None on record → seven, each with an owner, a description and a Proxy
   * - AI provider keys outside Smarter
     - In scripts, notebooks, a spreadsheet and a CI variable → none
   * - Revoking one project's access
     - Rotate a shared key, and break every project that used it → deactivate its Smarter API key
   * - Who spent what on AI
     - One vendor invoice a month, charged to IT → tokens and cost by project, person and department
   * - AI spending limit
     - A yearly budget line, overrun by 27% → a monthly budget per department, enforced on its Proxies and assistants
   * - Projects sending private records to an AI provider
     - Three: every salary, every student's record, the whole ledger → none
   * - Course designs sent to an AI provider
     - All 48 courses' modules and lessons, with every question on the website → none; at most ten rows of
       ``courses``
   * - Tokens per call, the three rebuilt projects
     - About 35,000 to 90,000 → about 1,000 to 3,000, the rows each question needs
   * - Endpoints a leaked project key could reach
     - Everything the provider account allows → the project's allowed paths, within its budget

For leadership, the change is the one an ERP made to the rest of the business. Before, AI was the one kind of
spending at Stackademy with no supplier list, no cost center, no owner and no register. After:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - What an ERP manages
     - What Smarter now manages for Stackademy's AI
   * - Approved suppliers
     - The AI providers that IT holds keys for, as Secrets; a project can reach no other
   * - Budgets and cost centers
     - A monthly budget per department, and the cost of every call, by project and person
   * - Roles and permissions
     - Who holds a key for each project, which endpoints it may call, and who may change its Proxy
   * - Asset register
     - Seven projects, each a named Proxy with a description and an owner; and, after phase 2, five assistants and
       their tools
   * - Audit trail
     - For every call, who made it, through which project, with which model and how many tokens; for the rebuilt
       projects, the conversation and every tool call

The prompt sizes are estimates that a reader can check. The ``gl_entries`` table has 2,502 lines, at roughly 35 tokens
each as a CSV row, about 88,000 tokens; ``stackademy_accounting_results`` returns three totals. The same arithmetic
applies to the 320 students and 725 enrollments of 2025, against one student's rows, and to the chatbot's 48
courses, 176 modules and 528 lessons, about 37,000 characters, against Stanley's ten rows.

Lessons for practitioners
-------------------------

- **Enable it, don't ignore it or ban it.** Ignored, shadow AI grows unseen; banned, it goes where you can't see it.
  Give people one place to build and run AI, and make it the easiest path, so that the governed way is the one they
  choose. Business teams build; IT governs.
- **Control the path before you change the projects.** A Proxy gives you keys, budgets and attribution for every
  project in the time it takes to change a base URL. Rebuilding a project to use its data safely takes days. Do the
  first for all of them, then the second for the ones that need it.
- **Don't break what people built.** Shadow AI is evidence of demand, built by people who needed it. A migration that
  keeps their projects running gets their help; one that shuts them down gets them hidden better.
- **A project on a platform outlives its author.** The ad copy drafter kept running, unknown, after the person who
  wrote it left. A project with a Proxy, a key and an owner in Smarter can be handed over; one on a laptop can't.
- **An invoice tells you how much, not what.** Spending only becomes manageable when each call is attributed to a
  project and a person, which needs one credential per project.
- **Prompt size is a smell.** A prompt of tens of thousands of tokens to answer a short question is a dataset in a
  prompt, and probably a leak. You don't need to store prompts to find it: their token counts point at the code to
  read.
- **Pasting the table is not retrieval.** Give the model tools that fetch the rows a question needs, over credentials
  that can read only what the department may see. It protects the data, and costs less.
- **Revoke last.** Rotating keys is a fine way to find what you missed, once everything you know of has moved.

Sources
-------

- The Stackademy repository, https://github.com/smarter-sh/stackademy: ``scripts/backoffice.sql`` (the
  ``ap_invoices`` of Cortex AI Services, account 5300, ``department_budgets``, ``expense_reports`` and
  ``gl_entries``), ``scripts/generate_backoffice.py``, ``budgets/``, and the department plugins in
  ``departments/accounting/plugins/``, ``departments/hr/plugins/`` and ``departments/admissions/plugins/``,
  ``plugins/api/stackademy-api.yaml`` and ``departments/it/guardrails/stackademy-pii-redaction.yaml``
- :doc:`/smarter-resources/smarter-proxy`, :doc:`/smarter-resources/smarter-secret` and
  :doc:`/smarter-platform/api-keys`
- :doc:`/smarter-resources/smarter-budget` and :doc:`/smarter-platform/cost-accounting`
- :doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-llmtool`,
  :doc:`/smarter-resources/smarter-mcpclient` and :doc:`/smarter-resources/smarter-guardrail`
- :doc:`ask-stanley`, for the rebuild of the website's course chatbot, and :doc:`confidential-by-construction`, for
  the departments' database users and budgets
