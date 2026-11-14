# pylint: disable=all
"""
The Smarter account, the root of the account tree, shares its resources with every account.

Before 0014, every account could read the Smarter account's resources because the read rule named it. Now an
account's ``share_scope`` decides, so the root's must be itself for every user to read what they read before.
Every other account keeps a null ``parent`` (directly under the root) and a null ``share_scope`` (shares
nothing), as before. See ADR-036 and :mod:`smarter.apps.account.hierarchy`.
"""

from django.db import migrations

from smarter.common.const import SMARTER_ACCOUNT_NUMBER


def forward(apps, schema_editor):
    Account = apps.get_model("account", "Account")
    root = Account.objects.filter(account_number=SMARTER_ACCOUNT_NUMBER).first()
    if root is None:
        # a new platform: Account.save() shares the root when initialize_platform creates it.
        return
    if root.share_scope_id is not None:
        return
    Account.objects.filter(pk=root.pk).update(share_scope_id=root.pk)


def reverse(apps, schema_editor):
    Account = apps.get_model("account", "Account")
    Account.objects.filter(account_number=SMARTER_ACCOUNT_NUMBER).update(share_scope_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0014_account_hierarchy"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
