"""Add SAMJournalBlob.last_used_at, which prune_journal_blobs uses to never delete a blob that is being reused."""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0009_samjournal_documents_samjournalblob"),
    ]

    operations = [
        migrations.AddField(
            model_name="samjournalblob",
            name="last_used_at",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
                help_text="When an entry last saved or reused the blob, to within a day. See SAMJournalBlobManager.prune.",
            ),
        ),
    ]
