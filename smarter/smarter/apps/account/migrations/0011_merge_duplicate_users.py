# pylint: disable=all
"""
Merge the users that share an email address, so that 0012 can make the address unique.

See :mod:`smarter.apps.account.user_merge`. The merge follows every relation to ``auth.User`` and
``account.UserProfile``, so this migration depends on the latest migration, at the time of writing,
of every app that has one: their models must be in the historical state that it receives.
"""

from django.db import migrations

from smarter.apps.account.user_merge import merge_duplicate_users


def forward(apps, schema_editor):
    merge_duplicate_users(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0010_contact_email_dates"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("connection", "0003_annotation_rows"),
        ("dashboard", "0002_onboardinghint"),
        ("drf", "0005_annotation_rows"),
        ("guardrail", "0002_annotation_rows"),
        ("journal", "0008_samjournal_image_search_plugin"),
        ("knox", "0009_extend_authtoken_field"),
        ("llmclient", "0013_llmclient_staff_only"),
        ("llmhost", "0003_annotation_rows"),
        ("llmtool", "0009_annotation_rows"),
        ("mcpclient", "0004_annotation_rows"),
        ("mcpserver", "0002_operations_tool_call"),
        ("orchestrator", "0002_annotation_rows"),
        ("prompt", "0002_annotation_rows"),
        ("provider", "0004_annotation_rows"),
        ("proxy", "0002_annotation_rows"),
        ("secret", "0002_annotation_rows"),
        ("social_django", "0017_usersocialauth_user_social_auth_uid_required"),
        ("taggit", "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx"),
        ("vectorsearch", "0002_annotation_rows"),
        ("vectorstore", "0002_annotation_rows"),
        ("waffle", "0004_update_everyone_nullbooleanfield"),
    ]

    operations = [
        # a merge can't be undone: the duplicates are deleted.
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
