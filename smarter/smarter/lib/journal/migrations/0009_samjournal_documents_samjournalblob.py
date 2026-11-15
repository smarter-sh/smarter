"""
Store the journal's documents as compressed skeletons and shared blobs.

See :mod:`smarter.lib.journal.storage`. The ``request`` and ``response`` JSON columns are replaced by
``request_document`` and ``response_document``. The journal was never enabled in production, so no
entry is converted.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0008_samjournal_image_search_plugin"),
    ]

    operations = [
        migrations.CreateModel(
            name="SAMJournalBlob",
            fields=[
                ("digest", models.CharField(editable=False, max_length=64, primary_key=True, serialize=False)),
                ("data", models.BinaryField(help_text="The blob's JSON, compressed with zlib.")),
            ],
        ),
        migrations.AlterField(
            model_name="samjournal",
            name="created_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False, null=True),
        ),
        migrations.RemoveField(
            model_name="samjournal",
            name="request",
        ),
        migrations.RemoveField(
            model_name="samjournal",
            name="response",
        ),
        migrations.AddField(
            model_name="samjournal",
            name="request_document",
            field=models.BinaryField(
                default=b"",
                help_text="The request's skeleton, compressed. See smarter.lib.journal.storage.",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="samjournal",
            name="response_document",
            field=models.BinaryField(
                default=b"",
                help_text="The response's skeleton, compressed. See smarter.lib.journal.storage.",
            ),
            preserve_default=False,
        ),
    ]
