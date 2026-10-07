# pylint: disable=all
"""
PluginDataSkill: add the remote skill source, and store bundled files with their contents.

Add the PluginMetaSkill admin proxy model.

``resources`` changes from a list of relative paths to a mapping of relative paths to file
contents. Existing paths are preserved, without contents.
"""

from django.db import migrations, models

import smarter.lib.json


def resources_list_to_dict(apps, schema_editor):
    PluginDataSkill = apps.get_model("plugin", "PluginDataSkill")
    for plugin_data in PluginDataSkill.objects.all():
        if isinstance(plugin_data.resources, list):
            plugin_data.resources = {str(path): None for path in plugin_data.resources}
            plugin_data.save(update_fields=["resources"])


def resources_dict_to_list(apps, schema_editor):
    PluginDataSkill = apps.get_model("plugin", "PluginDataSkill")
    for plugin_data in PluginDataSkill.objects.all():
        if isinstance(plugin_data.resources, dict):
            plugin_data.resources = list(plugin_data.resources)
            plugin_data.save(update_fields=["resources"])


class Migration(migrations.Migration):

    dependencies = [
        ("plugin", "0002_plugindataskill_alter_pluginmeta_plugin_class"),
    ]

    operations = [
        migrations.AddField(
            model_name="plugindataskill",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="The URL from which this skill was retrieved, if it was sourced remotely, e.g. from a GitHub repository.",
                max_length=2048,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="plugindataskill",
            name="source_retrieved_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When this skill was last retrieved from its source_url.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="plugindataskill",
            name="resources",
            field=models.JSONField(
                blank=True,
                default=dict,
                encoder=smarter.lib.json.SmarterJSONEncoder,
                help_text="The skill's bundled files (e.g. scripts/, references/, assets/), keyed by path relative to the skill root. A null value denotes a file whose contents are unavailable, such as a binary asset.",
            ),
        ),
        migrations.RunPython(resources_list_to_dict, resources_dict_to_list),
        migrations.CreateModel(
            name="PluginMetaSkill",
            fields=[],
            options={
                "verbose_name": "Plugin Meta (Skill)",
                "verbose_name_plural": "Plugin Meta (Skill)",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("plugin.pluginmeta",),
        ),
    ]
