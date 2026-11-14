# pylint: disable=all
"""
Demote the superusers that administer a customer's account, rather than the platform.

``manage.py initialize_account`` made an existing user it set up as an account's administrator a superuser, and
``get_cached_admin_user_for_account()`` made the ``<account number>-admin`` user it created for an account without an
administrator a superuser too. A superuser may read every account, so each of them could read every other
customer's resources. Both now make the user the administrator of that account only, with
``UserProfile.is_account_admin`` (ADR-036).

This migration demotes the superusers they already made. A legitimate superuser, a platform operator, belongs to
the Smarter account, and keeps their status. Every other superuser:

- is no longer a superuser;
- stays, or becomes, staff, which is how the web console recognizes an account's administrator, so that they keep
  its administrative controls;
- administers each account they belong to, with ``is_account_admin`` on each of their profiles.

It can't be reversed: afterwards, nothing tells which users it demoted.
"""

from django.conf import settings
from django.db import migrations

from smarter.common.const import SMARTER_ACCOUNT_NUMBER


def forward(apps, schema_editor):
    Account = apps.get_model("account", "Account")
    UserProfile = apps.get_model("account", "UserProfile")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)

    smarter_account = Account.objects.filter(account_number=SMARTER_ACCOUNT_NUMBER).first()
    if smarter_account is None:
        # a new platform: it has no superuser yet but the one initialize_platform creates.
        return
    operator_ids = UserProfile.objects.filter(account=smarter_account).values_list("user_id", flat=True)
    demoted = User.objects.filter(is_superuser=True).exclude(pk__in=list(operator_ids))
    demoted_ids = list(demoted.values_list("pk", flat=True))
    if not demoted_ids:
        return
    User.objects.filter(pk__in=demoted_ids).update(is_superuser=False, is_staff=True)
    UserProfile.objects.filter(user_id__in=demoted_ids).update(is_account_admin=True)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("account", "0016_user_profile_is_account_admin"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
