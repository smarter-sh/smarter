# pylint: disable=all
"""
Make ``auth_user.email`` unique, ignoring blank addresses.

See :func:`smarter.apps.account.user_merge.create_unique_email_index`. Users with the same address
that were created after 0011 ran are merged first, so that the index can be built.
"""

from django.db import migrations

from smarter.apps.account.user_merge import (
    create_unique_email_index,
    drop_unique_email_index,
    merge_duplicate_users,
)


def forward(apps, schema_editor):
    merge_duplicate_users(apps)
    create_unique_email_index(schema_editor)


def reverse(apps, schema_editor):
    drop_unique_email_index(schema_editor)


class Migration(migrations.Migration):

    # MariaDB commits DDL immediately, so it can't run inside a transaction.
    atomic = False

    dependencies = [
        ("account", "0011_merge_duplicate_users"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
