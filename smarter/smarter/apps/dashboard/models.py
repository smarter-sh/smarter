"""Dashboard models."""

from django.contrib.auth.models import User
from django.db import models

# our stuff
from smarter.lib.django.models import TimestampedModel


class EmailContactList(TimestampedModel):
    """Model to persist emails collected from landing page."""

    email = models.EmailField(unique=True, blank=False, null=False)

    class Meta:
        """Metadata for the model."""

        verbose_name = "Email Contact"
        verbose_name_plural = "Email Contacts"


class OnboardingHints(models.TextChoices):
    """
    The web console's onboarding hints, which point a new user to where to go next.

    Each id is also in the React package ``@smarter/onboarding``, ``OnboardingHints`` in its
    ``src/lib/const.ts``, which shows them.
    """

    SIDEBAR_LLMCLIENTS = "sidebar_llmclients", "The sidebar's LLM Clients link"
    LLMCLIENT_WEATHER = "llmclient_weather", "The Get Weather LLMClient in the list of LLMClients"
    WORKBENCH_TOUR = "workbench_tour", "The guided tour of the Prompt Engineer's Workbench"


class OnboardingOutcomes(models.TextChoices):
    """What the user did with an onboarding hint, which then never shows by itself again."""

    CLICKED = "clicked", "Clicked what the hint pointed to"
    DISMISSED = "dismissed", "Dismissed the hint"
    COMPLETED = "completed", "Completed the tour"
    VISITED = "visited", "Was already where the hint points to"


class OnboardingHint(TimestampedModel):
    """
    An onboarding hint that a user has seen, and what they did with it.

    A hint shows by itself until the user has a row for it, in any of their accounts, so that it
    shows once per user, on any device. ``created_at`` is when they first saw it to the end.

    :param user: The Django user.
    :param hint: The hint, one of :class:`OnboardingHints`.
    :param outcome: What the user did with it, one of :class:`OnboardingOutcomes`.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="onboarding_hints")
    hint = models.CharField(max_length=64, choices=OnboardingHints.choices)
    outcome = models.CharField(max_length=32, choices=OnboardingOutcomes.choices)

    class Meta:
        """Metadata for the model."""

        verbose_name = "Onboarding Hint"
        verbose_name_plural = "Onboarding Hints"
        unique_together = ("user", "hint")

    def __str__(self) -> str:
        return f"{self.user}: {self.hint} ({self.outcome})"
