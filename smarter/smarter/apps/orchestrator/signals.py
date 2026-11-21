"""
Signals of the orchestrator app.

They announce the Orchestrator's api calls and each step of a run's lifecycle: a run is queued
by :func:`smarter.apps.orchestrator.runtime.start_run`, then started, stepped and finished by
:func:`smarter.apps.orchestrator.runtime.execute_run`, in a Celery worker. A run's signals let the
platform observe it, e.g. to notify the user who started it, or to meter its steps, without
polling its status.

Example::

    from django.dispatch import receiver
    from smarter.apps.orchestrator.signals import orchestration_run_finished

    @receiver(orchestration_run_finished)
    def notify(sender, run, **kwargs):
        ...
"""

from django.dispatch import Signal

orchestrator_called = Signal()
"""
Signal triggered when a orchestrator is called.

Arguments:
    orchestrator (Orchestrator): The orchestrator instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    orchestrator_called.send(sender=self.__class__, orchestrator=self.orchestrator, request=request, args=args, kwargs=kwargs)
"""

orchestration_run_queued = Signal()
"""
Sent when a run is recorded, ``pending``, and its execution is queued.

Arguments:
    run (OrchestrationRun): The run.

Example::

    orchestration_run_queued.send(sender=start_run, run=run)
"""

orchestration_run_started = Signal()
"""
Sent when a worker starts to execute a run, whose status is now ``running``.

Arguments:
    run (OrchestrationRun): The run.

Example::

    orchestration_run_started.send(sender=execute_run, run=run)
"""

orchestration_step_finished = Signal()
"""
Sent when a step of a run is recorded, whether its LLMClient answered or the step failed.

Arguments:
    run (OrchestrationRun): The run.
    step (OrchestrationStep): The step, whose ``status`` is ``succeeded`` or ``failed``.

Example::

    orchestration_step_finished.send(sender=self.__class__, run=run, step=step)
"""

orchestration_run_finished = Signal()
"""
Sent when a run ends, with its final status: ``succeeded``, ``failed`` or ``max_iterations_exceeded``.

Arguments:
    run (OrchestrationRun): The run, whose ``status``, ``result``, ``error_message`` and
        ``iteration_count`` are final.

Example::

    orchestration_run_finished.send(sender=finish, run=run)
"""
