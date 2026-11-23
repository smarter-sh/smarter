"""
The progress of a Vectorstore's deploy: its conditions, its attempts, and its last error.

Creating a vector database takes minutes: Pinecone initializes a new index, and a self-hosted
Qdrant server needs a volume, an image and a pod that starts. Each of those can fail on its own,
and most failures are temporary. So ``deploy`` only checks what it can check at once, e.g. that
Pinecone accepts the api key, and queues the Celery task
:func:`~smarter.apps.vectorstore.tasks.deploy_vectorstore`, which checks the database again every
:data:`DEPLOY_CHECK_INTERVAL` seconds, backs off after an error, and gives up after
:data:`DEPLOY_MAX_ATTEMPTS` checks.

:class:`VectorstoreDeploymentState` is what the task records, in the Vectorstore's ``deployment``
column. The Vectorstore manifest's ``status`` and the REST api's vectorstore show it, so that a
person, or the web console, can follow a deploy: which conditions are met, which attempt it is
on, when it checks again, and why the last attempt failed.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from django.utils import timezone
from pydantic import BaseModel, Field

from smarter.apps.vectorstore.manifest.models.vectorstore.status import (
    SAMVectorstoreCondition,
    VectorstoreConditionStatusValue,
    VectorstoreConditionTypeValue,
)

if TYPE_CHECKING:
    from smarter.apps.vectorstore.models import VectorstoreMeta

CREDENTIALS: VectorstoreConditionTypeValue = "Credentials"
VOLUME: VectorstoreConditionTypeValue = "Volume"
SERVER: VectorstoreConditionTypeValue = "Server"
INDEX: VectorstoreConditionTypeValue = "Index"
CONDITION_ORDER: tuple[VectorstoreConditionTypeValue, ...] = (CREDENTIALS, VOLUME, SERVER, INDEX)
"""The conditions in the order that a deploy meets them, which is the order that they are shown."""

TRUE: VectorstoreConditionStatusValue = "True"
FALSE: VectorstoreConditionStatusValue = "False"
UNKNOWN: VectorstoreConditionStatusValue = "Unknown"

DEPLOY_CHECK_INTERVAL = 15
"""Seconds between the checks of a deploy that is waiting, e.g. for a server to start."""
DEPLOY_MAX_BACKOFF = 300
"""The longest wait, in seconds, after errors: the wait doubles after each error in a row, up to this."""
DEPLOY_MAX_ATTEMPTS = 80
"""The checks that a deploy makes before it fails, about 20 minutes of waiting."""
DEPLOY_STALLED_AFTER = timedelta(minutes=10)
"""A deploy whose next check is this late lost its Celery task, and Celery Beat's reconcile takes it over."""


class VectorstoreDeploymentState(BaseModel):
    """
    The progress of a Vectorstore's last deploy, as the deploy task records it.

    It is stored as JSON in :attr:`VectorstoreMeta.deployment
    <smarter.apps.vectorstore.models.VectorstoreMeta.deployment>`. Read it with :meth:`of`, and
    save it with :meth:`save_to`.
    """

    id: str = Field(default="", description="The deploy's id. A deploy's task stops when another deploy replaces it.")
    attempt: int = Field(default=0, description="The number of checks made.")
    maxAttempts: int = Field(default=DEPLOY_MAX_ATTEMPTS, description="The checks made before the deploy fails.")
    consecutiveErrors: int = Field(
        default=0, description="The errors in a row, which set the wait before the next check."
    )
    provisioned: bool = Field(default=False, description="Whether the database's infrastructure was created.")
    nextRetryAt: Optional[datetime] = Field(default=None, description="When the deploy checks again.")
    lastError: Optional[str] = Field(
        default=None, description="The deploy's last error, which may have been retried since."
    )
    finishedAt: Optional[datetime] = Field(default=None, description="When the deploy ended, ready or failed.")
    conditions: List[SAMVectorstoreCondition] = Field(default_factory=list, description="What the database needs.")

    @classmethod
    def of(cls, vectorstore: "VectorstoreMeta") -> "VectorstoreDeploymentState":
        """
        Return a Vectorstore's deployment state.

        :param vectorstore: The Vectorstore.
        :returns: Its state, or an empty one if it was never deployed.
        """
        data = vectorstore.deployment or {}
        state = cls.model_validate(data)
        return state

    @classmethod
    def start(cls) -> "VectorstoreDeploymentState":
        """Return the state of a new deploy, with a new id."""
        state = cls(id=uuid4().hex)
        return state

    def save_to(self, vectorstore: "VectorstoreMeta") -> None:
        """
        Save the state on a Vectorstore.

        :param vectorstore: The Vectorstore.
        """
        vectorstore.deployment = self.model_dump(mode="json")
        vectorstore.save(update_fields=["deployment", "updated_at"])

    @property
    def in_progress(self) -> bool:
        """Whether a deploy began and hasn't ended."""
        return bool(self.id) and self.finishedAt is None

    def is_stalled(self, now: Optional[datetime] = None) -> bool:
        """
        Whether a deploy in progress lost its Celery task: its next check is long overdue.

        :param now: The time, by default now.
        :returns: True if the deploy's next check is later than :data:`DEPLOY_STALLED_AFTER`.
        """
        if not self.in_progress:
            return False
        if self.nextRetryAt is None:
            return False
        now = now or timezone.now()
        stalled = now - self.nextRetryAt > DEPLOY_STALLED_AFTER
        return stalled

    def condition(self, condition_type: str) -> Optional[SAMVectorstoreCondition]:
        """
        Return a condition.

        :param condition_type: Its type, e.g. ``Index``.
        :returns: The condition, or None if it hasn't been recorded.
        """
        for condition in self.conditions:
            if condition.type == condition_type:
                return condition
        return None

    def set_condition(
        self,
        condition_type: VectorstoreConditionTypeValue,
        status: VectorstoreConditionStatusValue,
        reason: str = "",
        message: str = "",
    ) -> SAMVectorstoreCondition:
        """
        Record a condition.

        Its ``lastTransitionTime`` changes only when its status changes, as in Kubernetes, so that it
        says how long a condition has been what it is.

        :param condition_type: The condition's type, e.g. ``Server``.
        :param status: ``True``, ``False`` or ``Unknown``.
        :param reason: One word, e.g. ``ImagePullBackOff``.
        :param message: What was found, for a person.
        :returns: The condition.
        """
        condition = self.condition(condition_type)
        if condition is None:
            condition = SAMVectorstoreCondition(type=condition_type, status=status)
            condition.lastTransitionTime = timezone.now()
            self.conditions.append(condition)
            self.conditions.sort(key=lambda each: CONDITION_ORDER.index(each.type))
        elif condition.status != status:
            condition.status = status
            condition.lastTransitionTime = timezone.now()
        condition.reason = reason
        condition.message = message
        return condition

    def backoff(self) -> int:
        """
        Return the seconds to wait before the next check.

        It is :data:`DEPLOY_CHECK_INTERVAL` while the deploy is only waiting, and doubles with each
        error in a row, up to :data:`DEPLOY_MAX_BACKOFF`.
        """
        seconds = DEPLOY_CHECK_INTERVAL * 2**self.consecutiveErrors
        seconds = min(seconds, DEPLOY_MAX_BACKOFF)
        return seconds


__all__ = [
    "CONDITION_ORDER",
    "CREDENTIALS",
    "DEPLOY_CHECK_INTERVAL",
    "DEPLOY_MAX_ATTEMPTS",
    "DEPLOY_MAX_BACKOFF",
    "DEPLOY_STALLED_AFTER",
    "FALSE",
    "INDEX",
    "SERVER",
    "TRUE",
    "UNKNOWN",
    "VOLUME",
    "VectorstoreDeploymentState",
]
