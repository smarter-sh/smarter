Governance Review: What a Real Organization Revealed About Who May Administer What
==================================================================================

*How loading one realistic organization into Smarter exposed twelve flaws in its access model, from a path for a
customer's staff to take over any account to credentials written to the logs, and how one rule replaced twenty.*

At a glance
-----------

.. list-table::
   :widths: 25 75

   * - Organization
     - The Smarter platform itself, reviewed while Stackademy's organization was being loaded into it.
   * - Challenge
     - Smarter's access model had been built and tested for customers that are one team, with one administrator.
       An organization of six accounts, with people in several of them and administrators of one department each,
       exercised paths that no test had.
   * - Solution
     - Treat every surprise during the load as a finding: reproduce it, rate it, trace it to its cause, fix the
       cause with a test that fails without the fix, and record it in a commit that says what was wrong. Replace
       every "is this user staff?" with one rule, ``user_administers_account()``.
   * - Smarter features
     - ADR-036's account administrator role, ``user_administers_account()``, the User and SmarterAuthToken brokers,
       migration ``account.0017``, ``mask_identifier()``
   * - Outcome
     - Twelve findings, one critical and two high, all fixed in Smarter 0.46.0 and smarter-console 1.1.12; the
       critical one found before it reached any release.

Executive summary
-----------------

Most access-control flaws are not found by reading the rule. They are found by using the system the way a real
organization would, and noticing what happens. Smarter's model had been sound for its common case, a customer that
is one team, with one administrator, using one account. Stackademy is not that customer: six accounts in a tree, ten
people, a chief executive in every account, a Head of IT who administers every account without being a platform
superuser, and department heads who administer one department each.

Loading it found twelve flaws. The most serious, rated critical here, was new: the first version of the rule that
decides who administers an account let any staff user administer *every* account, so that a staff user of one
customer could add themselves to another customer's account as its administrator, through an ordinary User
manifest. It was found and fixed before it reached a release. Two high-rated flaws had shipped: tools that set up a
customer account made its administrator a *platform superuser*, able to read every other customer's resources; and
a staff user could mint an api key for a user of another account.

The remaining findings were of three kinds: resources resolved, or applied, in the wrong account; credentials, a
chat session key and the CSRF token, written to logs that the web console shows its users in debug mode; and stale
caches, failing pages and test data that left superusers behind.

Each was fixed at its cause, with a test that fails without the fix. The structural fix was to make one function,
``user_administers_account()``, the only place that decides who administers an account, and to call it from every
broker, the api key broker and the console's session, in place of some twenty separate checks of ``is_staff``.

Background
----------

Before this work, Smarter had two kinds of privileged user, both Django flags on the user, not on a membership:

- A **superuser** may do anything, in every account.
- A **staff** user administers the accounts they belong to, and may open the Django administration site.

Each broker, the code that applies a kind of manifest, checked ``is_staff`` itself where it meant "may administer
this account". ADR-036 added a third kind: the **account administrator**, ``UserProfile.is_account_admin``, a role
on one membership, which administers that account and nothing else, and opens no administration site.

Stackademy needed it. Its Head of IT administers every department's account; each department's head administers
their own; the chief executive belongs to every account. That is how real companies are organized, and the
platform had never been run that way.

The challenge
-------------

The review had to answer three questions about every surprise:

1. **Is it a flaw, or a mistake in the organization's declaration?** Several surprises were Stackademy's own
   manifests; most were not.
2. **How bad is it?** Who could exploit it, to do what, and had it shipped?
3. **Where is its cause?** A symptom fixed where it shows, e.g. an extra membership deleted by hand, comes back.

And the fixes had to keep every existing customer working: a platform operator must keep their powers, and an
existing customer's administrator must keep administering their own account, whatever else changes.

Options considered
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 36 36

   * - Option
     - For
     - Against
   * - Fix each finding where it showed
     - Quick, local, low risk per change
     - Twenty checks of ``is_staff`` would still each decide "administers" in their own way; the next role change
       would need twenty edits again
   * - A permissions framework: roles, permissions and grants as data
     - Flexible; familiar from enterprise products
     - A large change to every broker and the console at once; more to get wrong than the problem needs
   * - **One rule in one function, called everywhere; each finding fixed at its cause** (chosen)
     - The rule is short enough to read and test exhaustively; every caller agrees by construction
     - Each caller had to be found and changed; the rule's first version was itself flawed (F1)

The solution
------------

**One rule.** ``user_administers_account(user, user_profile)`` decides, everywhere, whether a user administers the
account of a profile:

- a **superuser** administers every account;
- anyone else needs **their own profile in the account**: staff then administer it, and anyone else only if the
  profile has ``is_account_admin``.

The second clause is the fix for F1. Its first version returned ``True`` for any staff user before it looked at
the profile. The User broker, applying a manifest whose ``spec.accounts`` named an account the applier didn't
belong to, asked the rule anyway, and it said yes.

.. figure:: /_static/case-studies/admin-rule.svg
   :alt: A table of roles and paths, before and after the review. Staff users went from every account to only
         those they belong to; account administrators administer their one account; customer administrators who
         were made superusers are demoted; api keys may be made only for users of one's own account.
   :width: 100%

   Exhibit 1. Who may administer an account, before and after the review.

**The findings register.** Each finding, its rating, whether it had shipped, and the commit that fixed it:

.. figure:: /_static/case-studies/findings-register.svg
   :alt: Twelve findings in four columns: who administers what, where resources resolve, credentials in logs, and
         reliability and hygiene. F1 is critical, F2 and F3 high, F4, F8 and F9 medium, the rest low.
   :width: 100%

   Exhibit 2. The review's twelve findings, by area and severity.

.. list-table::
   :header-rows: 1
   :widths: 6 44 12 38

   * - ID
     - Finding
     - Rating
     - Fix
   * - F1
     - Staff users administered every account, member or not, so a staff user of one customer could make
       themselves another account's administrator with a User manifest. Introduced and fixed before any release.
     - Critical
     - The rule requires the user's own profile in the account; a test proves the escalation is refused
       (``d2ca9533a``)
   * - F2
     - ``manage.py initialize_account`` made an account's administrator a platform superuser, and an account
       without an administrator got one created as a superuser: each could read every other customer's resources.
     - High
     - Both make an account administrator instead; migration ``0017_demote_account_superusers`` demotes the
       superusers they had made, except the platform's own operators (``a2c849cd0``)
   * - F3
     - A staff user could mint an api key for a user of another account. Separately, department heads who
       weren't staff couldn't create api keys at all.
     - High
     - The key's user must belong to the applier's account, and be neither a superuser nor, unless the applier is,
       staff; administrators may create keys (``242786138``)
   * - F4
     - Creating an account added the platform's administrator to it, through a lookup that fell back to the
       platform's admin, so that admin belonged to every account an Account manifest created.
     - Medium
     - A new account gets an administrator of its own (``3b31966dc``)
   * - F5
     - A user in several accounts applied manifests in an arbitrary one of them.
     - Low
     - ``apply_manifest`` and ``load_from_github`` act in the account given (``3b31966dc``)
   * - F6
     - A plugin was looked up through the account administrator's profile, so a member's plugin wasn't found, and
       loading it again failed creating a duplicate.
     - Low
     - Look it up by account and name, whoever owns it (``07b7483ec``)
   * - F7
     - An assistant's guardrails were resolved among the applier's resources, not the account tree, so departments
       couldn't use IT's shared guardrail.
     - Low
     - Resolve by account tree, nearest first, as connections do (``d3a61ba17``)
   * - F8
     - Every log stream connection wrote the user's username, and the full chat session key, a credential, to the
       server's log: in production, 628 lines with usernames and 43 with session keys in 25 hours.
     - Medium
     - Log the user's id and the masked key (``b6c92e5b2``)
   * - F9
     - The web console wrote the CSRF token and request bodies to the browser's console.
     - Medium
     - Removed in smarter-console 1.1.12, which Smarter pins (``699391c0f``)
   * - F10
     - Cached copies of a user's profiles kept an old role, or an old default account, until they expired.
     - Low
     - Refresh them on every save and delete (``242786138``, ``bac4e6fbf``)
   * - F11
     - A manifest page answered 500 for an owner whose default profile was in another account.
     - Low
     - Describe a resource through its own profile (``bac4e6fbf``)
   * - F12
     - Test runs had left 236 accounts without members and about 335 users without a profile in the development
       database, 9 of them superusers.
     - Low
     - Find test rows by the factories' marks, and purge before and after each run (``5ab7ed5b7``)

The ratings are this case's, by who could exploit a flaw and what it gave them: critical for taking over another
customer's account, high for reading another customer's data or acting as another customer's user, medium for
exposure of a credential or an unintended membership, low for a defect without a path to another customer.

Implementation
--------------

The review followed one routine for every finding:

1. **Reproduce** it, in the development stack, with the organization as declared.
2. **Trace** it to its cause. F6, for example, showed as a database ``IntegrityError`` on the chief executive's
   plugins; its cause was a lookup by account that silently became a lookup by one user.
3. **Write the failing test first**, then the fix. F1's test applies a User manifest as a staff user of one account
   that names another, and expects a refusal; the flawed rule fails it.
4. **Fix the cause, not the instance.** F2's migration demotes every superuser that the old code had made, on
   every platform, not only the ones found.
5. **Record it** in the commit message: the problem, how it showed, the fix, the tests, and any upgrade note. F2's
   commit tells operators that a customer administrator who was a superuser keeps administering their own accounts
   and loses the rest.

Two choices in the fixes are worth noting. The migration that demotes superusers can't be reversed, because
afterwards nothing records whom it demoted, so its reverse is an explicit no-op, and the commit says so. And
logging was fixed by logging less, an id and a masked key, rather than by filtering what is logged: a filter fails
open when a new field appears.

Results
-------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Measure
     - Result
   * - Findings
     - 12: 1 critical, 2 high, 3 medium, 6 low
   * - Fixed
     - All 12, in Smarter 0.46.0 and smarter-console 1.1.12, each with tests
   * - Places that decide "administers this account"
     - From about twenty checks of ``is_staff`` to one function
   * - Customer administrators who were platform superusers
     - Demoted by migration, on every platform that upgrades
   * - Credentials in the server's log
     - None from the log stream: ids and masked keys only
   * - The critical finding
     - Found and fixed before any release

Lessons for practitioners
-------------------------

- **Test with a realistic organization.** Every finding here came from loading an organization shaped like a real
  company. A suite of tests that each create one account and one administrator can't find a flaw that needs two
  accounts and a person in both.
- **Make the authorization rule a single function.** Twenty checks drift; one can be read in a minute and tested
  case by case. F1 was in the one function, and so was found once and fixed once.
- **Membership first, then role.** Every check of "may administer" must start from the user's own membership in the
  account in question. A global flag that grants power without a membership is a path into every account.
- **Convenience tools are part of the attack surface.** F2 came from setup commands that made a user a superuser
  because that was the quickest way to make them powerful enough.
- **Logs are an output.** If any user can see them, and in debug mode the console shows them, they must hold no
  credentials and no personal data. Log ids and masked values.
- **Fix the past, not only the future.** A data migration that repairs what the flaw already did is part of the
  fix.

Teaching notes
--------------

**Discussion questions**

1. Rate the twelve findings yourself, with your organization's scale. Where do you disagree with this case's
   ratings, and why?
2. F1 was introduced by the same change that added the account administrator role, and caught before release.
   What in the process caught it? What would have caught it sooner?
3. The demotion migration can't be reversed. Under what circumstances is an irreversible migration acceptable?
   What would you tell operators before they upgrade?
4. The Head of IT administers every department. Write the rule that would let them manage connections and Secrets,
   but not, say, the department's assistants. Is the extra rule worth its complexity?

**Exercises**

1. Read ``user_administers_account()`` in ``smarter/smarter/apps/account/models/user_profile.py`` and its tests.
   Write a table of every combination of superuser, staff, own profile and ``is_account_admin``, with the rule's
   answer for each.
2. Reconstruct F1: in a scratch branch, restore the rule's first version, and run
   ``test_user_broker_permissions.test_staff_of_another_account_add_no_members``. Explain the failure.
3. Search the Smarter codebase for remaining uses of ``is_staff``. For each, decide whether it means "may open
   the Django admin" or "administers this account", and whether it should call the rule.
4. Review a log of your own platform's dev server for usernames, emails, session keys and tokens, with the
   ``smarter-log-review`` skill's scanner, and write up what you find.

Sources
-------

- :doc:`ADR-036: Account Hierarchy and Resource Sharing </adr/036-account-hierarchy>`
- ``smarter/smarter/apps/account/models/user_profile.py`` (``user_administers_account()``),
  ``migrations/0017_demote_account_superusers.py``, ``manifest/brokers/user.py``,
  ``smarter/smarter/lib/drf/manifest/brokers/auth_token.py``
- Smarter commits ``d2ca9533a``, ``a2c849cd0``, ``242786138``, ``3b31966dc``, ``07b7483ec``, ``d3a61ba17``,
  ``b6c92e5b2``, ``bac4e6fbf``, ``5ab7ed5b7`` and ``699391c0f``; smarter-console 1.1.12
- :doc:`organizing-for-ai`, for the organization whose load found them
