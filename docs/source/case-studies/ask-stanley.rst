Ask Stanley: Answers for Prospective Students, at Any Hour
==========================================================

*Prospective students ask Stackademy the same questions every day, from eleven countries and at all hours. Its
website's first chatbot answered them from an old copy of the course brochures, and sent every course design
Stackademy owns to an AI provider with each question. With Smarter, an assistant answers from the course catalogue
itself, the moment the question is asked, and the AI provider sees only the few courses that answer it.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy, an online code academy: 48 courses priced between $450 and $1,000; 320 individual students in its
       fiscal year 2025, from 11 countries; an Admissions and Sales department of a director and three advisors.
   * - Problem
     - Prospective students need timely and accurate answers: which courses there are, what they cost, what to take
       first. Advisors answer accurately, but only during their working day. The website's chatbot, built before
       Stackademy had an AI platform, answered at once, but from a copy of the course brochures and outlines that
       nothing kept up to date, and it sent all 48 course designs, Stackademy's know-how, to its AI provider with
       every question.
   * - Solution
     - ``stackademy_sql``, an LLMClient called **Stanley**, which answers prospective students in plain language
       from the catalogue in Stackademy's own database, through one reviewed SQL query, over a read-only database
       user. It was the first of the departments' own AI projects that Stackademy rebuilt on Smarter, as
       :doc:`shadow-ai` tells.
   * - Smarter features
     - LLMClient; SqlPlugin; SqlConnection and Secret; Budget; Smarter Chat and ``allowedOrigins``; manifests in a git
       repository; and a Proxy, for the chatbot it replaced, until it did.
   * - Outcome
     - Every prospective student can get an answer at any hour, from the catalogue as it is at that moment. Every
       course, price and prerequisite in an answer comes from the database. The AI provider sees at most ten rows
       of the catalogue per question, and none of its course designs. Five manifests, no code, and at most $2,500 a
       month.

Executive summary
-----------------

A prospective student who asks *"My budget is $1,000. What courses can I take?"* is deciding whether to enroll, and
will decide with or without an answer. Stackademy's three Admissions Advisors answer well: they know the catalogue,
the prices and which course leads to which. But they work one time zone's office hours, and most of Stackademy's
students don't live in it. A question asked in Manila or Lagos in the evening waits until the next morning in North
America, and some students don't wait.

Admissions had already tried the obvious remedy, an AI chatbot on the website, before Stackademy had an AI
platform. A developer built it as a simple RAG solution: the course brochures and an export of every course's
outline, pasted into the prompt of every question. It answered at once, and it had two faults that grew with time.
Its knowledge was a copy, made once from whatever marketing material the developer had at hand, and nothing kept it
up to date: new courses were missing, and old prices stayed. And every question, from anyone on the internet, sent
the AI provider all 48 courses with their 176 modules and 528 lessons, which are Stackademy's course designs, its
know-how, unreleased courses included. Being fast and wrong is worse than being slow and right, because a student may
enroll on the strength of the wrong answer; and being fast by giving away the course designs is a cost no one had
chosen.

When Stackademy brought its departments' AI projects under Smarter, the chatbot was the first it rebuilt. The goal
was **both**: the speed of a chatbot and the accuracy of an advisor, without the giveaway. Stanley, the LLMClient
``stackademy_sql``, gets its speed from the AI model and its accuracy from the database. It has one tool, a
SqlPlugin whose query searches the ``courses`` table by subject and by price; the model chooses the values, Smarter
runs the query, and the model answers from the rows that come back. Those rows are the catalogue as it is at that
moment, and they are all the provider sees: a few courses' codes, names, descriptions, prices and prerequisites,
never their modules or lessons. Stanley is told not to guess, and to decline questions that aren't about
Stackademy's courses.

Stanley is also safe to put in front of strangers. It reads the database as ``stackademy_catalog``, a user that may
read only the catalogue's four tables, and it can't write a query of its own. A Budget caps what it may spend, so
that a public chat window can't run up an unbounded bill. And it was built from five manifests, with no code.

Background
----------

Stackademy is an online code academy. Its 48 courses run from **CS101 Introduction to Computer Science** to
**CS408 Professional Practice**, each with a code, a short description, a price between $450 and $1,000, and
usually one prerequisite: **CS301 Machine Learning** follows **CS210 Artificial Intelligence**, which follows **CS107
Algorithms**. Most of the company's revenue comes from nine corporate team licenses, which Admissions' director
negotiates; the rest comes from individual students, 320 of them in 45 cohorts in fiscal year 2025, who find the
courses themselves.

Those students are international. In 2025, 87 of them were in the United States, and 233, almost three in four,
were elsewhere: Canada and the United Kingdom, 40 each, then India, Mexico, the Philippines, Nigeria, Brazil,
Germany, France and Australia. Before they enroll, they ask the same few questions, and those questions are what
Stanley's chat window now suggests:

- *"Do you offer any courses on AI?"*
- *"My budget is $1,000. What courses can I take?"*
- *"I want to study programming. What do you suggest?"*

The answers are all in one table. The catalogue is the ``courses`` table of Stackademy's MariaDB database,
``stackademy``, which also holds the back office of every department (see :doc:`confidential-by-construction`).
When Course Content publishes a course or changes a price, it changes that table, and nowhere else.

How each course is taught is in two more tables, ``course_modules`` and ``lessons``: 176 modules and 528 lessons,
with their titles, order, lengths and status. They are Course Content's work, and what sets Stackademy's courses apart
from anyone else's, and they include courses that aren't released yet. A prospective student needs none of it to
choose a course.

The first chatbot
~~~~~~~~~~~~~~~~~

Admissions' first chatbot was one of the AI projects that Stackademy's departments built for themselves, before the
company had a platform for them (:doc:`shadow-ai` tells how it found them all). A developer wrote it with an AI
provider's SDK and the provider's API key, and gave it its knowledge the quickest way: the course brochures that
Admissions had at hand, and an export of every course's modules and lessons, pasted into the prompt of every
question. Retrieval in name only, it sent more than 10,000 tokens of course material with a one-line question.

In the first phase of bringing the projects under control, the chatbot kept running unchanged, through a Smarter
Proxy, which gave it a key, a budget and its own charges. Those charges are what singled it out: its prompts were
hundreds of times longer than its questions. Stanley replaced it in the second phase. The first chatbot is this
case's scenario, as the other legacy projects are in :doc:`shadow-ai`; Stanley, his manifests and the database are
real.

The people
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 26 22 30

   * - Person
     - Title
     - Department
     - Their part in this case
   * - Dmitri Dumont
     - Admissions Director
     - Admissions and Sales
     - Wants no prospective student left without an answer
   * - Wren Dumont
     - Admissions Advisor
     - Admissions and Sales
     - Answers prospective students by email and by phone
   * - Tomas Hartigan
     - Head of IT
     - Information Technology
     - Owns the catalogue's database user, connection and password
   * - Odette Eriksen
     - Head of Course Content
     - Course Content
     - Owns the catalogue: what each course is, and when it's ready

The prospective students themselves never sign in to Smarter. They are anyone, anywhere, who opens the chat.

The challenge
-------------

The problem is to give every prospective student an answer that is both:

1. **Timely.** An answer while the student is still deciding, at whatever hour that is where they live, not on the
   next business day in North America.
2. **Accurate.** Real courses, real codes, real prices and real prerequisites, as they are in the catalogue today.
   An answer that names a course that doesn't exist, or quotes last year's price, is worse than no answer. Nothing
   that has to be copied by hand stays accurate.

And four constraints apply to any solution:

3. **Need to know.** Send the AI provider only what a question needs. The course designs are Stackademy's know-how, and
   no prospective student's question needs them.
4. **Safe to expose.** The chat is public, so whatever it can reach, anyone on the internet can try to reach. It
   must not be able to read a student's record, an employee's salary, or any table but the catalogue.
5. **Bounded in cost.** Every question costs tokens, and on a public page the number of questions isn't Stackademy's
   to decide. The spending must be.
6. **No software project.** IT has two engineers, and a platform to run. Whatever is built must not need them to
   write, host and maintain a chatbot application.

Options considered
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - Keep the website's chatbot, the brochures and course outlines pasted into every prompt (the status quo)
     - Fluent, immediate, already built; on its Proxy, it has a key and a budget
     - Its copy goes out of date with the first new course or price, and no one owns keeping it current; every
       question sends all 48 course designs to the AI provider; more than 10,000 tokens per question; a model that
       doesn't find the answer in its prompt may still invent one
   * - Advisors answer by email and phone
     - Accurate and personal; advisors can also sell
     - One time zone's office hours for students in eleven countries; three people; the same three questions,
       answered by hand, every day
   * - More advisors, or an advisors' night shift
     - Accurate, and more hours covered
     - The advisor position Admissions filled in 2025 paid $52,000 to $60,000 a year; around-the-clock cover takes
       several, to answer mostly the same questions
   * - A FAQ page and a price list on the website
     - Always available; cheap
     - Can't answer a combined question, such as *"AI, under $800, and what do I need first?"*; a copy of the
       catalogue drifts from the catalogue
   * - Refresh the chatbot's copy from the database every night
     - Up to date within a day; little to change
     - Still sends the whole catalogue, and the course designs, with every question; still pays for them in tokens
   * - An assistant that writes its own SQL over the database
     - Answers anything the database can
     - On a public page, anyone may phrase the question that writes the query; every table the user can read is
       one question away
   * - **An assistant with one reviewed SQL query over a read-only catalogue user** (chosen)
     - Answers from the live catalogue, at any hour; what it can ask the database is known in advance; no code
     - It answers only what its query can: a narrower search than an advisor's memory (see `What Stanley doesn't
       do yet`_)

Stackademy also built a second Stanley, ``stackademy_api``, which reads the same catalogue through its REST API
with an ApiPlugin instead, and answers the same questions. The two are a side-by-side comparison of the two most
common kinds of tool, not competing options: Admissions' advisors use the API one on the phone, as
:doc:`organizing-for-ai` tells. This case is about the SQL one, which reads the database directly.

The solution
------------

Stanley is five resources, each declared in a manifest in the repository ``smarter-sh/stackademy``, each doing one
job:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Resource
     - Its job
   * - Secret ``stackademy_catalog_db_password``
     - Holds the database password, encrypted. Nothing else spells it out, and the model never sees it.
   * - SqlConnection ``stackademy_catalog_db``
     - Says how to reach the database, as the read-only user ``stackademy_catalog``, and names the Secret.
   * - SqlPlugin ``stackademy_sql``
     - The one tool: a reviewed query over ``courses``, with two values the model may fill in.
   * - LLMClient ``stackademy_sql``
     - Stanley himself: the model, his instructions, his tool, his chat window and its colors.
   * - Budget ``stackademy_project``
     - Caps what Stanley and his tool may spend.

.. figure:: /_static/case-studies/stanley-architecture.svg
   :alt: A prospective student, on any web site in allowedOrigins, talks to Stanley, the LLMClient stackademy_sql,
         on the Smarter platform. Stanley asks the AI model, gpt-6-luna, which answers with a tool call and never
         sees the database. Stanley's one tool, the SqlPlugin stackademy_sql, runs through the SqlConnection
         stackademy_catalog_db and its Secret, which sends a SELECT to the MariaDB database stackademy as the
         read-only user stackademy_catalog and gets rows of the courses table back. The user may read the courses,
         cohorts, modules and lessons tables; 21 other tables, such as students and employees, are refused. A
         Budget of $2,500 a month surrounds Stanley and his tool.
   :width: 100%

   Exhibit 1. How Stanley is wired: the AI model writes the sentences, and the database supplies the facts.

How Stanley answers a question
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A student asks *"Do you offer any courses on AI?"*. Smarter sends the question to the model, with a description of
Stanley's one tool. The model doesn't answer; it asks for the tool to be run, with ``description = AI``. Smarter
puts that value into the query as a parameter, never as SQL text, runs it as ``stackademy_catalog``, and hands the
rows back to the model:

.. figure:: /_static/case-studies/stanley-tool-call.svg
   :alt: A sequence of eight messages between four parties: the student, Stanley on Smarter, the AI model and
         MariaDB. 1, the student asks "Do you offer any courses on AI?". 2, Stanley sends the model the question and
         the tool's description. 3, the model answers with a tool call, description = AI. 4, Stanley sends MariaDB
         the reviewed query, with AI bound as a parameter. 5, MariaDB returns four rows of the courses table: CS210
         Artificial Intelligence, 700.00, prerequisite CS107 Algorithms; CS316 AI for Robotics, 850.00; CS319 AI in
         Healthcare, 800.00; and CS405 AI Capstone Project, 1000.00, the last three after CS301 Machine Learning. 6,
         Stanley sends the model the rows. 7, the model writes an answer from them. 8, Stanley gives the student the
         answer, in seconds.
   :width: 100%

   Exhibit 2. One question, from the chat to the database and back. The model never touches the database; Smarter
   runs the query and hands it the rows.

The model then answers from those four rows: the courses, their codes and prices, and where to start, CS210, whose
prerequisite is CS107. Every fact in the answer is one the database returned. The Prompt Engineer's Workbench shows
the whole exchange, in its console's **Tool Calls** tab: the tool, the values the model chose, and the rows that
came back.

The tool: one reviewed query
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SqlPlugin is a query that IT wrote and reviewed once, and two parameters that the model may fill in, each
described in words the model understands. Both are optional, so a question with no subject, or no budget, still
runs. The subject is one of six that the catalogue's descriptions use:

.. code-block:: yaml

   # plugins/sql/stackademy-sql.yaml (abridged)
   apiVersion: smarter.sh/v1
   kind: SqlPlugin
   metadata:
     name: stackademy_sql
   spec:
     selector:
       directive: always
     connection: stackademy_catalog_db
     sqlData:
       limit: 10
       sqlQuery: SELECT c.course_code, c.course_name, c.description, c.cost,
           prerequisite.course_code AS prerequisite_course_code,
           prerequisite.course_name AS prerequisite_course_name
         FROM courses c
         LEFT JOIN courses prerequisite ON c.prerequisite_id = prerequisite.course_id
         WHERE ((c.description LIKE CONCAT('%', {description}, '%')) OR ({description} IS NULL))
           AND (c.cost <= {max_cost} OR {max_cost} IS NULL)
         ORDER BY c.prerequisite_id;
       parameters:
         - name: max_cost
           type: number
           required: false
           description: the maximum cost that a student is willing to pay for a course.
         - name: description
           type: string
           required: false
           enum: [AI, mobile, web, database, network, neural networks]
           description: areas of specialization for courses in the catalogue.

Smarter does what would otherwise be the software project: it describes the tool to the model in the format that
the AI provider expects, binds the model's values into the query so that they can't change it, connects through a
pool with a timeout, trims the result to ten rows, and runs the conversation until the model has its answer.

Accurate: the database, not the model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stanley's accuracy doesn't depend on the model knowing Stackademy. It depends on three things that don't change
with the model:

- **The catalogue is the source.** The query reads ``courses`` at the moment of the question. When Odette Eriksen's
  team publishes a course, or a price changes, Stanley's next answer has it. There is no copy to update.
- **Stanley is told not to guess.** His instructions: *"When given the opportunity to utilize function calling, you
  should always do so ... DO NOT GUESS. IF YOU DON'T KNOW THE ANSWER, RESPOND THAT YOU DON'T KNOW."*
- **Stanley stays on topic.** The plugin's instructions tell the model to defer to the tool for anything about the
  courses, and to answer anything else with *"I am sorry, but I can only provide information about the courses
  offered by Stackademy University."* A student who asks for the capital of France is politely declined.

Need to know: only what the question needs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first chatbot sent everything it knew with every question, so that the model could find the answer. Stanley
sends nothing until the model asks, and then only what the query returns:

- **Only matching courses.** The query filters ``courses`` by the subject and the price that the model chose, and
  Smarter trims the result to ten rows. *"Do you offer any courses on AI?"* sends the provider four courses, not 48.
- **Only what a student needs to choose.** Each row is a course's code, name, short description, price and
  prerequisite. The query never reads ``course_modules`` or ``lessons``, so the course designs never reach the
  provider, whatever is asked.
- **Smaller, and cheaper.** A question costs a few hundred tokens of course data, where the first chatbot's cost
  more than 10,000.

Timely: a chat window that never closes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stanley answers in seconds, at any hour, as many students at once as ask. His chat window is a Smarter Chat, which
the LLMClient's manifest configures, down to Stackademy's colors, and which suggests the three questions students
ask most:

.. code-block:: yaml

   # llm-clients/stackademy-sql.yaml (abridged)
   apiVersion: smarter.sh/v1
   kind: LLMClient
   metadata:
     name: stackademy_sql
   spec:
     config:
       prompt:
         allowedOrigins:
           - https://smarter.sh   # the web sites that may embed Stanley's chat, once he's deployed
         deployed: false
         provider: openai
         defaultModel: gpt-6-luna
         appName: Stackademy SQL
         appAssistant: Stanley
         appWelcomeMessage: Welcome to Stackademy! How can I help you today?
         appExamplePrompts:
           - "Do you offer any courses on AI?"
           - "My budget is $1,000. What courses can I take?"
           - "I want to study programming. What do you suggest?"
     plugins:
       - stackademy_sql

Putting Stanley on a website is two steps. Deploying him gives him a host of his own, with a chat api that any
web page may call; ``allowedOrigins`` lists the sites whose pages may call it from a browser. The page itself
embeds Smarter Chat, the ``@smarter.sh/ui-chat`` component, or uses the WordPress, Drupal or Shopify integration.
The repository loads Stanley undeployed, so that each platform decides when, and where, he goes public.

Safe to expose: the catalogue, and nothing else
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stanley's connection reads the database as ``stackademy_catalog``, which may read four tables: ``courses``,
``cohorts``, ``course_modules`` and ``lessons``. Not ``students``, not ``enrollments``, not ``employees``, not
``compensation``. So even a query that someone persuaded Stanley to run couldn't reach a student's record; and
Stanley can't write one anyway, because his only tool is a fixed query. The database's own grants, checked on
every load, are what keep the rest of the company's records out of reach of a public chat window
(:doc:`confidential-by-construction` explains them).

The password belongs to IT. Tomas Hartigan's team keeps it in a Secret, which the connection names, so the model,
the chat and the log never see it. This one is a published demonstration password, which is why it can be in a
public repository; a real one never is.

Bounded: a budget with a hard stop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A deployed LLMClient without api keys is public, and its prompts are charged to its owner. So Stanley and his tool
have a Budget: $2,500 a month, and $10,000 over the project's six months. At 80% of the month's limit the owner is
warned; at the limit, Stanley stops, and says so:

.. code-block:: yaml

   # budgets/stackademy-project.yaml (abridged)
   apiVersion: smarter.sh/v1
   kind: Budget
   metadata:
     name: stackademy_project
   spec:
     config:
       unit: cost
       period: month
       periodicLimit: 2500.00
       absoluteLimit: 10000.00
       duration: 6
       action: block
       warningThreshold: 80
       message: The Stackademy project has used its budget. Please contact the project owner.
     resources:
       - kind: LLMClient
         name: stackademy_sql
       - kind: SqlPlugin
         name: stackademy_sql

How each role uses it
~~~~~~~~~~~~~~~~~~~~~

**Prospective students** ask Stanley whatever they would have emailed Admissions, whenever they think of it, and
get an answer before they close the page.

**Wren Dumont, Admissions Advisor,** no longer answers *"Do you have AI courses?"* by hand, every morning, for the
students who wrote overnight. The questions that reach Wren are the ones that need a person: a payment plan, a
company's team license, a student who isn't sure the course is right for them.

**Dmitri Dumont, Admissions Director,** gets the coverage of an around-the-clock team without hiring one, and keeps
the advisors for the conversations that sell.

**Tomas Hartigan, Head of IT,** owns what must stay central: the read-only database user, its connection, and the
Secret. Neither of IT's engineers wrote or hosts a chatbot application; the query is the only code-like thing they
wrote, and they wrote it once.

**Odette Eriksen, Head of Course Content,** owns the catalogue, and so, without doing anything new, what Stanley
says. A course is in Stanley's answers from the moment it is in ``courses``.

What Stanley doesn't do yet
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stanley's answers are accurate to the catalogue, but the catalogue and the query are not the whole truth, and a
practitioner should see where:

- **The search reads descriptions only.** *"AI"* finds the four courses whose description contains it. It doesn't
  find **CS301 Machine Learning**, **CS302 Deep Learning**, **CS303 Natural Language Processing** or **CS308 AI
  Ethics**, whose descriptions don't; a student hears of CS301 only as the prerequisite of three of the four. And
  subjects outside the six, such as cloud or security, can only be asked without a subject, which returns the first
  ten courses, the introductory ones.
- **The catalogue says nothing about when.** The ``courses`` table has no dates. Of the four AI courses, CS405 AI
  Capstone Project is still being made, and CS210 and CS316 had no cohort in 2025, so a student who asks when they
  can start gets no answer from Stanley. ``stackademy_catalog`` may already read ``cohorts``, so a second tool needs
  no new grant, only a second reviewed query.
- **There is no guardrail.** Stanley's chat is public, and a student may type personal details into it. The
  departments' assistants use IT's ``stackademy_pii_redaction`` guardrail; Stanley doesn't, yet.

Each of these is a change to a manifest, reviewed as a pull request, not a software project.

Implementation
--------------

Replacing the first chatbot took one change on the website: its chat window gave way to Stanley's, a Smarter Chat
embedded in the page. The old chatbot's Proxy was then deactivated, so that nothing could still call it with its
key, and its brochures and course export were deleted.

Stanley is the oldest part of the Stackademy repository, and the reason it exists. The project's manifests, its checks
and its README arrived in one commit, ``837ce4b``; ``6129664`` let ``smarter.sh`` embed both Stanleys' chats, with
``allowedOrigins``; ``4ae399e`` linked their chat windows' info to this case study; and ``3f0f9bc`` renamed the course
database and its resources to ``stackademy`` when the departments' back office joined it.

Every Smarter platform loads the repository when it is set up: ``initialize_platform`` calls ``load_from_github``,
which runs the repository's ``pre`` script,
``scripts/create-course-database.sh``, which creates the database and its users and checks their grants, and then
applies the manifests in the order of their dependencies: the Secret, the SqlConnection, the SqlPlugin, the
LLMClient and the Budget. So Stanley is in a new platform's account, working, the first time anyone signs in.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Before → after
   * - When a prospective student can get an answer
     - Advisors' office hours, in one time zone → any hour, in seconds
   * - Students it serves
     - 320 individual students in 2025, 233 of them outside the United States, in ten other countries
   * - Where an answer's courses, prices and prerequisites come from
     - An advisor's knowledge of the catalogue → the ``courses`` table, at the moment of the question
   * - Where the courses in an AI's answer come from
     - The first chatbot's copy of the brochures, as old as its last paste → only the rows Stanley's tool returns,
       from the live catalogue, under instructions not to guess
   * - Course data sent to the AI provider per question
     - All 48 courses, 176 modules and 528 lessons, more than 10,000 tokens → at most ten rows of ``courses``, a few
       hundred tokens
   * - Course designs sent to the AI provider
     - Every module and lesson, unreleased courses included, with every question → none
   * - Tables a public chat can reach
     - 4 of the database's 25, the catalogue's, through one fixed query; no student or employee record
   * - What it took to build
     - Five manifests, and one SQL query; no application code, nothing for IT to host
   * - Cost
     - At most $2,500 a month and $10,000 over six months, with a warning at 80% and a hard stop
   * - Advisors' time on the three common questions
     - Answered by hand, every day → left to Stanley; advisors keep the questions that need a person

Lessons for practitioners
-------------------------

- **Timely and accurate come from different places.** The model makes an answer fast; only your own data makes it
  right. An assistant needs both, and a chatbot that answers from a copy has only the first.
- **Ask the source, don't copy it.** A catalogue pasted into a prompt, or onto a FAQ page, starts going out of date
  the day it's copied. A tool that queries the table at the moment of the question can't.
- **Pasting everything is not retrieval.** A prompt that carries your whole catalogue gives your know-how to the AI
  provider with every question, and pays for it in tokens. A tool sends the rows the question needs, and nothing it
  doesn't ask for.
- **On a public page, fix the query.** A model that writes SQL answers more, but on the internet the question is
  anyone's to phrase. One reviewed query, over a user that can read only what the public may see, makes the worst
  question harmless.
- **Accurate is not the same as complete.** Stanley never names a course that doesn't exist, but his search misses
  courses that do. Test an assistant on the questions students actually ask, and widen its tools where they fall
  short.
- **Put a price on public.** You don't decide how many strangers will ask. A budget with a hard stop decides how
  much they can cost.

Sources
-------

- The Stackademy repository, https://github.com/smarter-sh/stackademy: ``llm-clients/stackademy-sql.yaml``,
  ``plugins/sql/stackademy-sql.yaml``, ``connections/sql/stackademy-catalog-db.yaml``,
  ``secrets/stackademy-catalog-db-password.yaml``, ``budgets/stackademy-project.yaml``, ``scripts/stackademy.sql``,
  ``scripts/backoffice-grants.txt``, and its README
- Stackademy commits ``837ce4b``, ``6129664``, ``4ae399e`` and ``3f0f9bc``
- :doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-llmtool` and
  :doc:`/smarter-resources/llmtool/how-tools-work`
- :doc:`/smarter-resources/smarter-connection`, :doc:`/smarter-resources/smarter-secret`,
  :doc:`/smarter-resources/smarter-budget`, :doc:`/smarter-resources/smarter-guardrail`
- :doc:`/smarter-framework/smarter-chat/embedding` and :doc:`/smarter-framework/smarter-integrations/smarter-wordpress`
- :doc:`The Stackademy page </smarter-framework/smarter-manifests/stackademy>`
- :doc:`shadow-ai`, for how Stackademy found its departments' AI projects, and rebuilt the first chatbot first
