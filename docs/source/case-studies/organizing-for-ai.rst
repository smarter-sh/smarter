Organizing for AI: Everyone Can Ask the Data
============================================

*Stackademy's data is all in open systems, SQL databases, REST APIs, services with MCP servers, but only two of its
40 employees have the skills to ask them anything new. With Smarter, everyone asks in plain language, and more
people answer more of their own questions.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy, an online code academy: 40 employees in seven departments; about $4.4 million of revenue, most of
       it from nine corporate team licenses (870 seats), the rest from 320 individual students.
   * - Problem
     - Not enough people can use the company's data. Getting a new answer out of it takes SQL, a REST API call or an
       MCP client, and only IT's two platform engineers have those skills. Everyone else gets the reports someone
       already built, and the rest of their questions go unasked.
   * - Solution
     - An AI assistant per department that turns a question in plain language into the right query, API call or
       search, over that department's own data only. IT's engineers set up each tool once; the department asks it
       anything, as often as it likes.
   * - Smarter features
     - LLMClients; SqlPlugins, ApiPlugins and MCPClients; SqlConnections and Secrets; an account per department and
       account administrators; a shared Guardrail; Budgets; an Orchestrator; manifests in a git repository.
   * - Outcome
     - The people who can ask the data a new question go from two to every employee who signs in. The quarterly board
       pack, a week of the CFO's work, takes one request. No department can read another's records.

Executive summary
-----------------

Stackademy did everything right with its systems. Its records are in an open database, its course catalog has a
REST API, and more of the services it uses offer MCP servers. Every answer the company needs is within
reach of anyone who can write SQL, call an API or drive an MCP client. At Stackademy that is two people, the
platform engineers in IT, and they have a platform to run.

So the company's data served the few questions that someone had already built a report for. The Admissions Director
couldn't ask how many of a corporate customer's people finished their courses before a renewal call; an HR Business
Partner couldn't compare pay across departments without a spreadsheet built by hand; the CFO spent a week each
quarter assembling a board pack from four departments' exports. The questions weren't hard. They were just out of
reach of the people who had them.

Stackademy's goal was **more**: more people asking more questions of the data the company already had. Smarter
gives each department an assistant that does the technical part. An employee asks in plain language; the assistant
picks an approved query, API call or search, runs it, and answers from what comes back. IT's engineers set up each
tool once, and the department asks it whatever it likes.

Opening the data to everyone is only acceptable if it stays as closed as before to everyone else. Each department
is a Smarter account that only its members may use, each assistant reads the database as its own department's user,
IT's guardrail removes personal data from every prompt, and the CFO sets each department's AI budget.

Who is Stackademy?
------------------

Stackademy is an online code academy. It offers 48 courses, from **CS101 Introduction to Computer Science** to
**CS408 Professional Practice**, in programming, databases, cloud and AI, priced between $450 and $1,000. Most of its
business is corporate training: nine companies buy team licenses, 870 seats in all, at between $270,000 and $745,000
a year each. It also teaches individual students, 320 of them in 45 cohorts in its fiscal year 2025. That year it had
40 employees and about $4.4 million of revenue, most of it from the team licenses.

Its systems are open. Everything it knows about itself, from payroll to the general ledger to every enrollment, is
in SQL databases. Its course catalog is published through a REST API. Nothing is
locked in a vendor's product. But open isn't the same as usable: the database answers SQL, the API answers HTTP
requests, and an MCP server answers an MCP client. Its IT department only has two people.

The organization and its people
-------------------------------

Stackademy has seven departments. Five of them now use AI assistants, and ten of its employees sign in to Smarter.
None of the ten writes SQL:

.. list-table::
   :header-rows: 1
   :widths: 22 26 22 30

   * - Person
     - Title
     - Department
     - What they want to ask
   * - Vera Jaramillo
     - Chief Executive Officer
     - Executive Office
     - How is the company doing, right now?
   * - Odette Hartigan
     - Chief Financial Officer
     - Finance and Accounting
     - Results against budget; the board pack
   * - Tomas Hartigan
     - Head of IT
     - Information Technology
     - How to give everyone the data, safely, with two engineers
   * - Avery Ivanova
     - HR Director
     - Human Resources
     - Headcount, pay and open positions
   * - Quinn Sandoval
     - HR Business Partner
     - Human Resources
     - One employee's record, time off, hiring
   * - Kofi Sandoval
     - Staff Accountant
     - Finance and Accounting
     - Overdue invoices, spending by department
   * - Odette Eriksen
     - Head of Course Content
     - Course Content
     - Which courses are late, and why
   * - Tomas Underhill
     - Instructional Designer
     - Course Content
     - The week's open production tasks
   * - Dmitri Dumont
     - Admissions Director
     - Admissions and Sales
     - Corporate contracts, before each customer call
   * - Wren Dumont
     - Admissions Advisor
     - Admissions and Sales
     - Courses, prices and cohorts, while a student is on the phone

The seventh department, Instruction, a dean and 14 instructors, doesn't use an assistant yet. Exhibit 0, in
:doc:`the introduction <index>`, shows the accounts, people and assistants together.

What the platform has to do
---------------------------

Putting the data in everyone's hands means doing four things that, until now, depended on the two engineers'
judgment:

1. **Translate.** Turn a question in plain language into a query, an API call or a search, and the result back
   into an answer, without anyone writing code.
2. **Gatekeep.** Limit access to sensitive information such as salaries only to HR, students' records only to Admissions, and the executives only totals.
3. **Protect.** Never send PII (Personally Identifiable Information) such as Social Security numbers or card numbers outside the company.
4. **Ration.** Keep the token cost of all those new questions within what each department can spend.

Smarter does the first with an assistant per department and its tools, and the other three with accounts,
database users, a guardrail and budgets. The rest of this case shows who does what.

How each role uses it
---------------------

The Head of IT: Tomas Hartigan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** IT had the only people in the company who could ask the data something new, and two of them were not
enough for a 40-employee company. **Now:** IT's engineers turn each kind of question into a tool once, and the departments ask
it as often as they like. IT keeps only what must stay central.

**Tools that need no technical skill to use.** Smarter gives an assistant three kinds of tool, one for each skill
the employees lack:

- A **SqlPlugin** is one approved SQL query, over a SqlConnection. The model fills in its values, such as an
  employee's name or a month, but can't write a query of its own. Stackademy's department assistants use these.
- An **ApiPlugin** is one approved call to a REST API. Stackademy's catalog assistant, Stanley, answers *"Do you
  offer any courses on AI?"* by calling the catalog's API.
- An **MCPClient** connects an assistant to an MCP server, and makes its tools, such as searching a code
  repository, a document store or the web, available to the assistant. IT adds one like a database connection, and a
  department head lists it in their assistant.

The engineers write each query, call or connection once, with the department that will use it. After that, nobody
needs to know it exists.

**An account per department.** Stackademy Corp is the company's account; IT, HR, Accounting, Course Content and
Admissions are accounts below it. Each account decides who may read its resources. IT's shares with the whole
company; every other department's, with its own members only:

.. figure:: /_static/case-studies/sharing.svg
   :alt: A tree of the Smarter platform, Stackademy Corp, and Stackademy IT, HR and Accounting below it. For a member
         of HR, the platform, IT and HR are readable; Corp and Accounting are not.
   :width: 100%

   Exhibit 1. What a member of Stackademy HR may read.

**The credentials, kept by IT.** Each department's database connection, a SqlConnection, and its password, a
Secret, belong to Tomas, but live in *the department's* account, where only its members may use them. Each connects
as its own database user, ``stackademy_hr`` for HR, which may read only that department's tables. No department
handles a database password, and a mistake in one assistant can't reach another department's records: the
database refuses it.

**One privacy guardrail for everyone.** IT's guardrail, ``stackademy_pii_redaction``, replaces US Social Security
and card numbers in every prompt with ``[REDACTED ...]`` before it goes to the AI provider. IT's account shares it
with the whole company, so every department's assistant uses it, and none builds its own.

**Administration without a superuser.** Tomas is an *account administrator* in all six accounts, so IT can fix any
department's connection, but holds no power over the platform or any other company on it.

**The organization, by pull request.** The accounts, the people, their memberships and who owns each folder of
resources are YAML manifests in the repository ``smarter-sh/stackademy``. A new hire, or a new department, is a pull
request that someone reviews, and the platform applies it as written.

.. code-block:: yaml

   # org/accounts/01-stackademy-it.yaml
   apiVersion: smarter.sh/v1
   kind: Account
   metadata:
     name: stackademy_it
     accountNumber: "2718-2818-0001"
   spec:
     config:
       companyName: Stackademy IT
       parent: "2718-2818-0000"       # under Stackademy Corp
       shareScope: "2718-2818-0000"   # every account under Stackademy Corp may use IT's resources

.. figure:: /_static/case-studies/org-as-code.svg
   :alt: The stackademy repository's folders on the left, load_from_github in the middle, and on the right each
         folder with the person who owns it and the account it lands in.
   :width: 100%

   Exhibit 2. The organization, declared in a git repository.

Human Resources: Avery Ivanova and Quinn Sandoval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** HR's screens showed one employee at a time. A question across employees, such as average pay by
department, meant an export and an afternoon in a spreadsheet, so mostly it wasn't asked. **Now:** Quinn asks
Harper, HR's assistant, and has the answer in the same conversation.

**Avery owns Harper.** Harper is an LLMClient in HR's account, with three SqlPlugins: headcount and pay by
department, one employee's record, and the open positions. Harper is told to answer only from its tools, and never
to guess a name, number or date. Avery decides when Harper is ready, and deploys it, without asking IT.

**Avery administers HR, and only HR,** so HR changes its own assistant on its own schedule, and can't see or change
anything of another department's.

**Quinn asks, and gets the answer.** *"What is our headcount and average salary by department?"* *"Which positions
are we hiring for?"* From HR's own records, through HR's own database user. An Admissions Advisor who opens the
console doesn't see Harper, or HR's connection, at all.

The CFO and Accounting: Odette Hartigan and Kofi Sandoval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** the accounting system's standard reports answered the questions its designers expected. Anything else,
such as each department's spending against budget, month by month, meant exporting the ledger and rebuilding it by
hand. **Now:** Kofi asks Ledger, Accounting's assistant, *"Which departments went over budget in December?"*, and
Odette asks it for the quarter's income statement.

**Odette owns Ledger,** whose tools report the quarter's results, the income statement, spending against budget,
and overdue invoices, each computed by the database, so the totals add up.

**Odette also sets the price of all those questions.** Each department's assistant and its tools are covered by a
Budget: $150 a month and $1,800 in all. At 80% of the month's limit the department is warned; at the limit, the
assistant stops, and tells its users to ask the CFO to raise it. More questions cost more, and the CFO decides how
much, per department, in one place.

Course Content: Odette Eriksen and Tomas Underhill
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** the production schedule was in the database, but nobody in Course Content could query it, so it was
reported by hand in a weekly status meeting. **Now:** Tomas Underhill, an Instructional Designer, starts the day by
asking Reel, Course Content's assistant, *"Which courses still have unpublished lessons?"*, and Odette Eriksen, its
head, knows which courses are late before the meeting, not during it.

Odette Eriksen owns Reel and its two tools, course status and production tasks, and administers the department.
Searching is the department's next step: its lessons and exercises live in code repositories, and an MCP server can
search them. Connected to Reel through an MCPClient, it would let an Instructional Designer ask *"Which lessons
still use Python 3.8?"* without knowing how to search a repository.

Admissions: Dmitri Dumont and Wren Dumont
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** Dmitri went into renewal calls with the contract on paper and without the numbers behind it. **Now:**
Dmitri asks Ada, Admissions' assistant, *"Which companies have the largest contracts?"* ten minutes before the call.
Wren, an Admissions Advisor, answers a prospective student's *"What can I take for under $1,000?"* while the student
is still on the phone, from the catalog's own API, through Stanley.

Dmitri owns Ada and its two tools, enrollments and corporate contracts. Ada's records are students' personal data,
so the same protections apply as to HR's: Ada lives in Admissions' account, connects as Admissions' own database
user, and uses IT's guardrail.

The executives: Vera Jaramillo and Odette Hartigan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Before:** the quarterly board pack was a week of the CFO's time, collecting figures from four departments and
reconciling them, and between quarters the chief executive's questions had no one to answer them. **Now:** Vera asks
Atlas, the executives' assistant, *"Prepare the board pack for Q4 2025"*, and gets one page: the quarter's results,
spending against budget, headcount and payroll, enrollments, and the courses still in production.

Atlas lives in the company's account, which only the executives may use. It reads the database as its own user,
``stackademy_executive``, which may read only totals, so no one's salary, and no student, reaches the board.

Vera can also have the departments answer for themselves. The Orchestrator ``stackademy_quarterly_board_pack`` asks
Harper, Ledger, Reel and Ada for their parts at the same time, each from its own records and charged to its own
department's budget, and Atlas combines them. Only someone who may use all four assistants may run it: Vera, who is
a member of every department, but not Odette Hartigan, who isn't a member of HR. :doc:`the-board-pack` tells that
story.

How it fits together
--------------------

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Job
     - What does it, in Smarter
     - Who owns it
   * - Translate
     - An LLMClient per department, with SqlPlugins, ApiPlugins and MCPClients, each set up once by IT's engineers
     - Each department head
   * - Gatekeep
     - An account per department; its SqlConnection and Secret in that account; a database user per department;
       account administrators
     - The head of IT
   * - Protect
     - A Guardrail in IT's account, shared with the whole company
     - The head of IT
   * - Ration
     - A Budget per department, with a warning and a hard stop
     - The CFO

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Before → after
   * - People who can ask the company's data a new question
     - Two platform engineers → every employee who signs in, ten so far
   * - Skills needed to ask
     - SQL, REST APIs, MCP clients → plain language
   * - The quarterly board pack
     - A week of the CFO's work → one request to Atlas
   * - IT's engineers' time on one-off reports
     - Most of it → setting up each tool once
   * - Who may see salaries, and students' records
     - Unchanged: HR's members, and Admissions'; the executives see only totals
   * - Personal data sent to an AI provider
     - None: Social Security and card numbers redacted from every prompt
   * - Cost
     - At most $150 a month per department, set by the CFO

Lessons for practitioners
-------------------------

- **Open systems aren't enough.** Data in an open database, behind a documented API, is still out of reach for
  anyone who can't write the query. Count the people who can actually ask, not the systems that could answer.
- **Spend scarce skills once.** Two engineers can't answer 40 people's questions, but they can write the tools that
  let 40 people answer their own.
- **Widen access and narrow exposure together.** Everyone can now ask; no one can ask about another department's
  records. Without the second, the first is a breach.
- **Keep central only what must be central.** Credentials, the privacy guardrail and the organization itself stay
  with IT; the assistants belong to the departments.
- **Put a price on more.** More questions cost more. A budget per department, with a hard stop and a named person
  who can raise it, makes that an ordinary management decision.

Sources
-------

- The Stackademy repository, https://github.com/smarter-sh/stackademy: ``org/accounts/``, ``org/users/``,
  ``owners.yaml``, ``departments/``, ``budgets/``, ``plugins/api/``
- :doc:`Accounts </smarter-resources/account/resources/account>` and
  :doc:`Users </smarter-resources/account/resources/user>`
- :doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-llmtool`,
  :doc:`/smarter-resources/smarter-mcpclient`, :doc:`/smarter-resources/smarter-connection`,
  :doc:`/smarter-resources/smarter-secret`
- :doc:`/smarter-resources/smarter-guardrail`, :doc:`/smarter-resources/smarter-budget`,
  :doc:`/smarter-resources/smarter-orchestrator`
- :doc:`The Stackademy page </smarter-framework/smarter-manifests/stackademy>`
