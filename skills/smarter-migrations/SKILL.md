---
name: smarter-migrations
description: Use when a Smarter Django model changes, or a choices enum used by a model changes (e.g. SmarterJournalThings), and a migration is needed. Covers the single-0001_initial preference, when to add a migration instead (released apps with data), data migrations for legacy rows, running makemigrations in the container, verifying with --check, and the MariaDB non-transactional DDL trap.
---

# Smarter Migrations

Migrations are generated and applied **inside the smarter-app container**, then
copied back to the host. See `smarter-docker-environment` for syncing.

## Choose: recreate 0001_initial, or add a migration

**Preference: one `0001_initial.py` per app, where possible.** When an app's
models change, delete its migrations and regenerate one clean initial
migration, rather than stacking up 0002, 0003, and so on. The `guardrail` app is
an example.

That's possible when the app is new or unreleased, or its tables hold no data
worth keeping:

```console
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py migrate <app> zero"
# delete smarter/smarter/apps/<app>/migrations/0*.py on the host and in the container
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py makemigrations <app>"
docker cp smarter-app:/home/smarter_user/smarter/smarter/apps/<app>/migrations/0001_initial.py smarter/smarter/apps/<app>/migrations/
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py migrate"
```

- `migrate <app> zero` also reverts the migrations of apps that depend on it.
  Check that they hold no data you need first.
- In your summary, say that existing databases need `migrate <app> zero` (or
  `--fake`) before they upgrade.

**Ask before collapsing a released app's migrations.** An app that has shipped
(llmclient, account, plugin, ...) has production rows. Add a new migration
instead, as `llmclient/migrations/0006_llmclientcustomdomain_ownership.py`
does.

## A new migration on a released app

1. Change the model.
2. Generate it in the container (`makemigrations <app> --name <what_it_does>`),
   or write it by hand when the generator can't express it (for example
   ownership added to existing rows).
3. **Existing rows need a data migration.** When you add a required field (an
   owner, a name, or a status), add it as nullable or with a default, fill it with
   `migrations.RunPython(forward, reverse)`, then `AlterField` it to its final
   form, and `AlterUniqueTogether` last. 0006 follows exactly this order.
4. In `RunPython` functions, use `apps.get_model("<app>", "<Model>")`, never an
   import of the real model. The historical model is what exists at that point.
5. Give `RunPython` a real reverse function when the forward step can be undone.
   Otherwise use `migrations.RunPython.noop`, explicitly.
6. Copy the file to the host.

## Choice changes need migrations too

Changing the `choices` of a model field, for example adding a kind to
`SmarterJournalThings` in `smarter/smarter/lib/journal/enum.py`, changes the
field's state. It needs an `AlterField` migration
(`lib/journal/migrations/0007_alter_samjournal_thing_custom_domain.py`).

## Verify

```console
# no model changes without a migration
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py makemigrations --check --dry-run"
# forward
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py migrate"
# backward, then forward again, with legacy-shaped rows in the table
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py migrate <app> <previous_migration> && python manage.py migrate <app>"
```

Test a data migration with rows shaped like production's (old rows, missing
values, duplicates that the new unique constraint would reject), not just an
empty table.

## MariaDB: DDL is not transactional

MariaDB commits each schema change immediately. When a migration fails halfway,
the steps before the failure **stay applied**, but Django records the
migration as unapplied. Re-running it then fails with errors like
`Duplicate column name 'is_verified'`.

To recover, compare the table with the migration (`SHOW CREATE TABLE`), finish
or undo the partial steps by hand, then record the right state with
`migrate <app> <migration> --fake`. Keep migrations small, and put risky data
steps in their own migration, so a failure leaves less to repair.

## Then

- Run the app's tests (`smarter-python-testing`).
- Mention the migration, and any upgrade step it needs, in the commit body.
