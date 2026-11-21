"""Django Signal Receivers for orchestrator."""

# pylint: disable=W0613,C0115

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import OrchestrationRun, OrchestrationStep, Orchestrator
from .signals import (
    orchestration_run_finished,
    orchestration_run_queued,
    orchestration_run_started,
    orchestration_step_finished,
    orchestrator_called,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


@receiver(orchestrator_called, dispatch_uid="orchestrator_called")
def orchestrator_called_receiver(sender, orchestrator: Orchestrator, **kwargs):
    """
    Log a request to an Orchestrator's api, at DEBUG.

    The request's data is not logged: a run's objective is whatever the user wrote.

    :param sender: The class that sent the signal, the Orchestrator api view.
    :param orchestrator: The Orchestrator that was called.
    :param kwargs: Other signal arguments: ``request``, ``data``, ``args`` and ``kwargs`` (unused).
    """
    logger.debug("called %s (id %s)", orchestrator, orchestrator.pk)


@receiver(orchestration_run_queued, dispatch_uid="orchestration_run_queued")
def orchestration_run_queued_receiver(sender, run: OrchestrationRun, **kwargs):
    """
    Log that a run was queued.

    Its objective is not logged: it is whatever the user who started the run wrote.

    :param sender: The function that sent the signal, ``start_run()``.
    :param run: The pending run.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info("queued run %s of orchestrator %s", run.pk, run.orchestrator_id)  # type: ignore[attr-defined]


@receiver(orchestration_run_started, dispatch_uid="orchestration_run_started")
def orchestration_run_started_receiver(sender, run: OrchestrationRun, **kwargs):
    """
    Log that a worker started to execute a run, and its strategy.

    :param sender: The function that sent the signal, ``execute_run()``.
    :param run: The running run.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info(
        "started run %s of orchestrator %s, strategy %s",
        run.pk,
        run.orchestrator_id,  # type: ignore[attr-defined]
        run.orchestrator.strategy,
    )


@receiver(orchestration_step_finished, dispatch_uid="orchestration_step_finished")
def orchestration_step_finished_receiver(sender, run: OrchestrationRun, step: OrchestrationStep, **kwargs):
    """
    Log a step of a run: its sequence, its harness's LLMClient, and whether it succeeded.

    A failed step logs at WARNING. Its error message is not logged: it may quote the LLM provider,
    so it is kept in the step's record.

    :param sender: The class that sent the signal, ``RunContext``.
    :param run: The run.
    :param step: The recorded step.
    :param kwargs: Other signal arguments (unused).
    """
    llmclient_name = step.harness.llmclient.name
    if step.status == OrchestrationStep.StepStatus.FAILED:
        logger.warning("step %s of run %s failed, llmclient %s", step.sequence, run.pk, llmclient_name)
        return
    logger.info("step %s of run %s succeeded, llmclient %s", step.sequence, run.pk, llmclient_name)


@receiver(orchestration_run_finished, dispatch_uid="orchestration_run_finished")
def orchestration_run_finished_receiver(sender, run: OrchestrationRun, **kwargs):
    """
    Log how a run ended: its final status and how many steps it took.

    :param sender: The function that sent the signal, ``finish()``.
    :param run: The finished run.
    :param kwargs: Other signal arguments (unused).
    """
    logger.info("run %s %s after %s steps", run.pk, run.status, run.iteration_count)


@receiver(post_save, sender=Orchestrator)
def orchestrator_saved(sender, instance: Orchestrator, created: bool, **kwargs):
    """
    Log the creation or update of an Orchestrator, with its name and id.

    Its serialized fields are not logged: they include the owner's user profile, whose
    email address is personal data.

    :param sender: The model class.
    :param instance: The Orchestrator that was saved.
    :param created: True if the Orchestrator was created, False if it was updated.
    """
    if created:
        logger.info("created %s (id %s)", instance, instance.pk)
    else:
        logger.info("updated %s (id %s)", instance, instance.pk)


@receiver(pre_delete, sender=Orchestrator)
def orchestrator_deleted(sender, instance: Orchestrator, **kwargs):
    """
    Log that an Orchestrator is about to be deleted.

    :param sender: The model class.
    :param instance: The Orchestrator being deleted.
    """
    logger.info("%s", instance)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache("Orchestrator", "orchestrator.Orchestrator", "orchestrator.OrchestratorHarness")
