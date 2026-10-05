# pylint: disable=all
"""
Give LLMClientCustomDomain the same ownership as every other Smarter resource:

it becomes a MetaDataWithOwnershipModel, with a user_profile, name, description,
version, tags and annotations.

Existing custom domains are owned by the owner of the llmclient that uses them,
or else by a superuser, and are named after their domain name.

is_verified is replaced by verification_status (Not Verified, Verifying,
Verified or Failed), verified_at and verification_message. Verified domains
stay Verified.
"""

import re

import django.db.models.deletion
import taggit.managers
from django.db import migrations, models

import smarter.lib.django.validators
import smarter.lib.json


def custom_domain_name(domain_name: str) -> str:
    """A copy of smarter.apps.llmclient.models.llmclient_custom_domain.custom_domain_name."""
    return re.sub(r"[^a-z0-9]+", "_", (domain_name or "").lower()).strip("_") or "custom_domain"


def set_owners_and_names(apps, schema_editor):
    LLMClientCustomDomain = apps.get_model("llmclient", "LLMClientCustomDomain")
    LLMClient = apps.get_model("llmclient", "LLMClient")
    UserProfile = apps.get_model("account", "UserProfile")

    custom_domains = LLMClientCustomDomain.objects.all()
    if not custom_domains.exists():
        return
    fallback_owner = (
        UserProfile.objects.filter(user__is_superuser=True).order_by("id").first()
        or UserProfile.objects.order_by("id").first()
    )
    for custom_domain in custom_domains:
        llmclient = LLMClient.objects.filter(custom_domain=custom_domain).first()
        user_profile = llmclient.user_profile if llmclient else fallback_owner
        if user_profile is None:
            raise RuntimeError(f"No UserProfile exists to own custom domain {custom_domain.domain_name}.")
        name = custom_domain_name(custom_domain.domain_name)
        candidate, i = name, 1
        while LLMClientCustomDomain.objects.filter(user_profile=user_profile, name=candidate).exists():
            candidate = f"{name}_{i}"
            i += 1
        custom_domain.user_profile = user_profile
        custom_domain.name = candidate
        custom_domain.save(update_fields=["user_profile", "name"])


def set_verification_status(apps, schema_editor):
    LLMClientCustomDomain = apps.get_model("llmclient", "LLMClientCustomDomain")
    for custom_domain in LLMClientCustomDomain.objects.filter(is_verified=True):
        custom_domain.verification_status = "Verified"
        custom_domain.verified_at = custom_domain.updated_at
        custom_domain.save(update_fields=["verification_status", "verified_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0001_initial"),
        ("llmclient", "0005_llmclientguardrails_unique"),
        ("taggit", "0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="name",
            field=models.CharField(
                default="",
                help_text="Name in camelCase, e.g., 'apiKey', no special characters.",
                max_length=255,
                validators=[
                    smarter.lib.django.validators.SmarterValidator.validate_snake_case,
                    smarter.lib.django.validators.SmarterValidator.validate_no_spaces,
                ],
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="A brief description of this resource. Be verbose, but not too verbose.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="version",
            field=models.CharField(
                blank=True,
                default="1.0.0",
                help_text="Semantic version in the format MAJOR.MINOR.PATCH, e.g., '1.0.0'.",
                max_length=255,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="annotations",
            field=models.JSONField(
                blank=True,
                default=list,
                encoder=smarter.lib.json.SmarterJSONEncoder,
                help_text="Key-value pairs for annotating this resource.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="tags",
            field=taggit.managers.TaggableManager(
                blank=True,
                help_text="Tags for categorizing and organizing this resource.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="user_profile",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="account.userprofile",
            ),
        ),
        migrations.RunPython(set_owners_and_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="llmclientcustomdomain",
            name="user_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="account.userprofile",
            ),
        ),
        migrations.AlterField(
            model_name="llmclientcustomdomain",
            name="aws_hosted_zone_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("Not Verified", "Not Verified"),
                    ("Verifying", "Verifying"),
                    ("Verified", "Verified"),
                    ("Failed", "Failed"),
                ],
                default="Not Verified",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="llmclientcustomdomain",
            name="verification_message",
            field=models.CharField(blank=True, default="", max_length=1024),
        ),
        migrations.RunPython(set_verification_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="llmclientcustomdomain",
            name="is_verified",
        ),
        migrations.AlterUniqueTogether(
            name="llmclientcustomdomain",
            unique_together={("user_profile", "name")},
        ),
    ]
