# pylint: disable=all
"""
Convert the names of existing API keys to snake_case.

SAM manifest names are snake_case, so ``describe SmarterAuthToken`` reported a key named
``smarter-admin-key`` as ``smarter_admin_key``, while ``get`` reported its stored name, and
describing the name that describe returned failed. ``SmarterAuthToken.save()`` now stores
names in snake_case. This converts the rows that were saved before it did.
"""

from django.db import migrations


def forward(apps, schema_editor):
    """Convert each API key's name to snake_case."""
    # pylint: disable=import-outside-toplevel
    from smarter.common.utils import to_snake_case
    from smarter.lib.django.validators import SmarterValidator

    SmarterAuthToken = apps.get_model("drf", "SmarterAuthToken")
    for token in SmarterAuthToken.objects.only("pk", "name").iterator():
        if token.name and not SmarterValidator.is_valid_snake_case(token.name):
            SmarterAuthToken.objects.filter(pk=token.pk).update(name=to_snake_case(token.name))


class Migration(migrations.Migration):

    dependencies = [
        ("drf", "0003_alter_smarterauthtoken_tags_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
