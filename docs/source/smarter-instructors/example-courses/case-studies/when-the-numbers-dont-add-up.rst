When the Numbers Don't Add Up: Assuring the Accuracy of AI Financial Reporting
==============================================================================

*How four errors in Stackademy's AI-reported figures, each plausible, one of them in every board pack, were found by
reconciling the assistants' answers with the books, and the controls that now prevent each kind.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - Stackademy's executives and its Accounting department, and their assistants, Atlas and Ledger.
   * - Challenge
     - The assistants reported revenue, expenses, net income and budget overruns that looked right, were formatted
       like a finance team's, and were wrong. Nothing failed, and nothing warned.
   * - Solution
     - Reconcile every reported figure with the database; let the database do every sum; give each figure one
       source; filter every total to its fiscal year; and check the reporting views against the ledger each time the
       database is loaded.
   * - Smarter features
     - SqlPlugin (fixed queries, row limits), LLMClient system roles, Orchestrator summarizer
   * - Outcome
     - Four errors found before any figure reached a real reader, the largest $4,620 of Q4 revenue and the
       difference between a quarter's loss of $10,008.07 and one of $5,388.07; four controls, three of them
       enforced by code rather than by instructions.

Executive summary
-----------------

The risk of AI in financial reporting is not that it produces nonsense. Nonsense gets caught. The risk is a figure
that is close, plausible, well formatted and wrong, delivered with the same confidence as a right one.

While building the executives' board pack (see :doc:`the-board-pack`), Stackademy compared each figure that its
assistants reported with the same figure computed directly from its database, a fixed, generated set of books
in which every answer is known. Four figures disagreed. Each disagreement had a different cause, and only one of
them was the model's arithmetic:

1. **Arithmetic by the model.** Atlas added up Q2's expense accounts itself, and was $4,000 out.
2. **Truncation.** A tool returned at most 25 rows, so a quarter's budget lines were cut short before the
   assistant summed them: Admissions was reported $20,548.92 over budget, not $21,659.57.
3. **A reporting view without a year.** The views behind the board pack grouped the ledger by quarter, not by
   quarter *and* year, so tuition prepaid in December 2024 was counted in Q4 2025. Every Q4 board pack overstated
   revenue by $4,620, and showed a loss of $5,388.07 where the books show one of $10,008.07.
4. **The wrong source winning.** When the Accounting assistant reported the right Q4 figure, Atlas, the summarizer,
   "corrected" it to the view's wrong one.

The fixes share a principle: a model may choose which figure to report, but it never computes one. Every total is
computed by the database, in one query per figure; every view is limited to its fiscal year; and the database's own
load script now fails unless the board's revenue equals the ledger's.

Background
----------

Stackademy's books are in its database: a chart of accounts, 2,502 general ledger lines from December 2024 to
December 2025, and each department's monthly budget by account. A generator writes them from a fixed random seed,
so the right answer to every question is known and stays the same. Its fiscal year 2025, as the ledger totals it:

.. list-table::
   :header-rows: 1
   :widths: 16 28 28 28

   * - Quarter
     - Revenue
     - Expenses
     - Net income
   * - Q1
     - 885,864.11
     - 978,630.16
     - (92,766.05)
   * - Q2
     - 1,264,186.17
     - 1,029,137.84
     - 235,048.33
   * - Q3
     - 1,170,382.42
     - 1,054,216.79
     - 116,165.63
   * - Q4
     - 1,081,466.17
     - 1,091,474.24
     - (10,008.07)
   * - **Year**
     - **4,401,898.87**
     - **4,153,459.03**
     - **248,439.84**

.. figure:: /_static/case-studies/quarterly-results.svg
   :alt: A bar chart of revenue and expenses for each quarter of 2025. Q1 and Q4 are losses. A faint cap on Q4's
         revenue bar marks the $4,620 that an early view wrongly counted.
   :width: 100%

   Exhibit 1. Stackademy's results by quarter, fiscal 2025.

Two assistants report on these books. **Ledger**, Accounting's, has tools over the ledger, budgets and invoices.
**Atlas**, the executives', has tools over five views of totals, and, in the orchestrated board pack, writes the
page from the departments' answers.

The challenge
-------------

None of the four errors produced an error message, a refusal or an obviously wrong number. A $4,000 slip in a
quarter's million dollars of expenses is under half a percent. A department $20,548.92 over budget is as believable
as one $21,659.57 over. A Q4 loss of $5,388.07 instead of $10,008.07 changes no headline: Q4 was a small loss
either way. Reviewing the answers by eye would not have found them.

So the challenge was twofold: to **find** errors that look exactly like right answers, and to **prevent** each
kind, in a way that doesn't depend on a model remembering an instruction.

Options considered
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - Better instructions: "be careful with arithmetic", "double-check totals"
     - Cheap; sometimes helps
     - A request, not a control; doesn't touch errors 2 and 3, which weren't the model's
   * - A stronger or larger model
     - Fewer arithmetic slips
     - Doesn't touch truncation, the view, or which source wins; costs more on every call
   * - A second model to review the first
     - Catches some slips
     - Two models that read the same wrong view agree on the wrong figure, as error 4 showed
   * - **Reconcile with the books, then move every computation into the database** (chosen)
     - Each figure has one computed source; each control is testable; the view is checked on every load
     - More SQL tools, each narrower; questions the tools don't anticipate get "I don't have that" rather than a
       guess

The solution
------------

**Find: reconcile.** Each figure that an assistant reported was recomputed from the ledger with a query written
independently of the tools, the way an auditor ties a report to the trial balance. Every difference was traced to
its cause before anything was changed.

.. figure:: /_static/case-studies/errors-and-controls.svg
   :alt: A table of four errors: arithmetic by the model, truncation by a 25-row limit, a view grouped by quarter
         without the year, and the summarizer trusting the flawed view. For each, what happened, its effect, and
         the control that now prevents it.
   :width: 100%

   Exhibit 2. Four errors, and the control that now prevents each.

**Prevent 1: the database adds up.** Each tool that reports a total computes it in SQL. Ledger's new
``stackademy_accounting_results`` returns a period's revenue, expenses and net income in one row; Atlas's
``stackademy_board_quarterly_results`` does the same by quarter. Both assistants' system roles forbid adding
figures up, and point to those tools.

.. code-block:: yaml

   # departments/accounting/plugins/stackademy-accounting-results.yaml (abridged)
   kind: SqlPlugin
   metadata:
     name: stackademy_accounting_results
     description: Revenue, expenses and net income for a period, e.g. a quarter of 2025, totalled by the database.
   spec:
     connection: stackademy_accounting_db
     sqlData:
       sqlQuery: |
         SELECT SUM(CASE WHEN a.account_type = 'revenue' THEN g.credit - g.debit ELSE 0 END) AS revenue,
           SUM(CASE WHEN a.account_type = 'expense' THEN g.debit - g.credit ELSE 0 END) AS expenses,
           SUM(g.credit - g.debit) AS net_income
         FROM gl_entries g
         JOIN chart_of_accounts a ON a.gl_account = g.gl_account
         WHERE a.account_type IN ('revenue', 'expense') AND g.entry_date BETWEEN {start_date} AND {end_date};

**Prevent 2: one row per answer.** The budget tool returned a row per department, month and account, which a
quarter overflowed. It now totals budget, actual spending and overspending in SQL, one row per department, or per
account for a department that is named. A row limit is then a safety net, not a silent cut.

**Prevent 3: every total in its fiscal year.** The board views that total by quarter or month now keep to the
fiscal year:

.. code-block:: sql

   CREATE OR REPLACE SQL SECURITY DEFINER VIEW `board_income_statement` AS
   SELECT QUARTER(g.entry_date) AS fiscal_quarter, MONTH(g.entry_date) AS fiscal_month, a.account_type, a.name AS account,
     CASE WHEN a.account_type = 'revenue' THEN SUM(g.credit - g.debit) ELSE SUM(g.debit - g.credit) END AS amount
   FROM gl_entries g
   JOIN chart_of_accounts a ON a.gl_account = g.gl_account
   WHERE a.account_type IN ('revenue', 'expense') AND YEAR(g.entry_date) = 2025
   GROUP BY QUARTER(g.entry_date), MONTH(g.entry_date), a.account_type, a.gl_account, a.name;

And the script that loads the database checks the views against the ledger, and fails if they disagree:

.. code-block:: console

   checked: the general ledger balances
   checked: the Board Pack's views total 2025, and nothing else

**Prevent 4: one source of truth.** With the view corrected, Atlas and Ledger compute Q4 from the same ledger, for
the same period, and agree. The summarizer's instructions say to quote the departments' figures as they are, and to
check a total with its own tools; that check is useful only because the tools now return the right total.

Implementation
--------------

The errors were found, and fixed, in the order they surfaced:

- **Error 1** appeared in Atlas's first version, and was fixed before it was released: the quarterly results tool
  and the rule against arithmetic are in the commit that adds Atlas (Stackademy ``639fd76``).
- **Errors 2, 3 and 4** appeared once the departments' assistants answered alongside Atlas, in the orchestrated
  board pack. Error 2 showed in a supervisor run of the departments; errors 3 and 4 in a Q4 board pack, whose
  revenue differed between Ledger's section and Atlas's summary. All three are fixed in one commit, ``e75319a``,
  whose message records the figures before and after.

That commit also adds the regression tests: the load script's reconciliation of the views with the ledger, a count
of the views' enrollments against the year's, and a test of the generator that every board view that totals by
quarter or month filters by the fiscal year. After the fix, asked for Q4, Ledger reports revenue of $1,081,466.17,
expenses of $1,091,474.24 and a net loss of $10,008.07, and the departments' overspending with Admissions first, at
$21,659.57; the orchestrated board pack uses the same figures.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Figure
     - Reported
     - Books
   * - Q2 expenses (Atlas, first version)
     - 1,033,137.84
     - 1,029,137.84
   * - Admissions, Q4 over budget (Ledger, supervisor run)
     - 20,548.92
     - 21,659.57
   * - Q4 revenue (board views)
     - 1,086,086.17
     - 1,081,466.17
   * - Q4 net income (board views)
     - (5,388.07)
     - (10,008.07)
   * - Prepaid December 2024 counted in Q4 2025
     - 16 ledger lines, 8 enrollments, $4,620
     - none

Each control is now enforced where it can't be forgotten: three in code (totals in SQL, the fiscal-year filter and
its test, the load script's reconciliation) and one in instructions, backed by tools that make it easy to follow.

Lessons for practitioners
-------------------------

- **Reconcile, don't review.** Plausible errors pass a reader. Tie every reported figure to the books, at least
  until each kind of figure has a control.
- **Never let a model do arithmetic that matters.** Compute every total where the data is. The model's job is to
  choose the right total and explain it.
- **Watch for silent truncation.** A row limit that cuts a result short looks exactly like a complete result. Make
  each answer one row, or make the tool say when it hit its limit.
- **A view is code.** Grouping by quarter without the year is a bug that every consumer inherits. Test views like
  code, against an independent computation.
- **A summarizer amplifies its sources.** An editor model trusts the source it was told to check with. If that
  source is wrong, it will overwrite the right answer. Give each figure one source.
- **Use data whose answers are known.** A fixed, generated dataset made every one of these errors detectable. Test
  AI reporting against books you can recompute, before you trust it with books you can't.

Teaching notes
--------------

**Discussion questions**

1. Error 4 is a model doing exactly what it was told: checking a total with its own tools. Who was at fault: the
   model, the instructions, or the tool? What does your answer imply for how you'd review an AI system?
2. The ledger starts in December 2024 because tuition is paid ahead. Is that a data error or a reporting error?
   How would a finance team handle prepaid tuition in the income statement?
3. Each fix narrows what the assistants can answer. When is "I don't have a tool for that" worse than an
   approximately right answer?
4. Which of these errors would a stronger model have avoided? Which would it have made worse?

**Exercises**

1. On a platform with Stackademy loaded, compute Q4 2025 revenue directly from ``gl_entries`` as
   ``stackademy_accounting``. Then ask Ledger and Atlas. Reconcile all three.
2. Recreate error 3: in a scratch database, define ``board_income_statement`` without the year filter, and find
   the rows that it counts in Q4 2025. Write the test that would have caught it.
3. Ask Ledger a question its tools can't answer, e.g. revenue by course for Q3. Record what it says, then write the
   SqlPlugin that answers it, with the total computed in SQL.
4. Design a reconciliation report that a finance team could run each quarter against the board pack: which
   figures, which queries, what tolerance, and who signs it.

Sources
-------

- The Stackademy repository: ``scripts/generate_backoffice.py``, ``scripts/create-course-database.sh``,
  ``departments/accounting/plugins/``, ``departments/executive/plugins/``: https://github.com/smarter-sh/stackademy
- Stackademy commits ``639fd76`` (Atlas, totals in SQL) and ``e75319a`` (the fiscal year, totals for Ledger, and
  the reconciliation checks)
- :doc:`the-board-pack`, for the orchestration in which errors 2 to 4 appeared
