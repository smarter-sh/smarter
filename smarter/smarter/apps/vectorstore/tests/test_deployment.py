"""Test the progress of a Vectorstore's deploy: :mod:`smarter.apps.vectorstore.deployment`."""

from datetime import timedelta

from django.utils import timezone

from smarter.apps.vectorstore.deployment import (
    CREDENTIALS,
    DEPLOY_CHECK_INTERVAL,
    DEPLOY_MAX_ATTEMPTS,
    DEPLOY_MAX_BACKOFF,
    DEPLOY_STALLED_AFTER,
    FALSE,
    INDEX,
    SERVER,
    TRUE,
    UNKNOWN,
    VOLUME,
    VectorstoreDeploymentState,
)
from smarter.apps.vectorstore.models import VectorstoreMeta

from .base_classes import VectorstoreTestBase


class TestVectorstoreDeploymentState(VectorstoreTestBase):
    """Test the state that the deploy task records, and the Vectorstore's status shows."""

    def test_a_vectorstore_that_was_never_deployed(self):
        """Test that a Vectorstore without a deploy has an empty state, which no deploy is in progress for."""
        vectorstore = self.new_vectorstore("test_deployment_never")
        state = VectorstoreDeploymentState.of(vectorstore)
        self.assertEqual((state.id, state.attempt, state.conditions), ("", 0, []))
        self.assertEqual(state.maxAttempts, DEPLOY_MAX_ATTEMPTS)
        self.assertFalse(state.in_progress)
        self.assertFalse(state.is_stalled())

    def test_saved_and_read_again(self):
        """Test that the state survives a round trip through the Vectorstore's deployment column."""
        vectorstore = self.new_vectorstore("test_deployment_saved")
        state = VectorstoreDeploymentState.start()
        state.attempt = 3
        state.lastError = "timed out"
        state.set_condition(SERVER, FALSE, "CrashLoopBackOff", "back-off restarting failed container")
        state.save_to(vectorstore)
        read = VectorstoreDeploymentState.of(VectorstoreMeta.objects.get(pk=vectorstore.pk))
        self.assertEqual(read, state)
        self.assertTrue(read.in_progress)
        self.assertEqual(len(read.id), 32)

    def test_conditions(self):
        """Test that a condition's transition time changes only with its status, and that conditions keep their order."""
        state = VectorstoreDeploymentState.start()
        index = state.set_condition(INDEX, UNKNOWN, "Pending")
        state.set_condition(SERVER, FALSE, "Starting", "The Qdrant server is starting.")
        state.set_condition(CREDENTIALS, TRUE, "Accepted")
        state.set_condition(VOLUME, TRUE, "Bound")
        self.assertEqual([c.type for c in state.conditions], [CREDENTIALS, VOLUME, SERVER, INDEX])

        server = state.condition(SERVER)
        assert server is not None
        started = server.lastTransitionTime
        state.set_condition(SERVER, FALSE, "ImagePullBackOff", "the image can't be pulled")
        self.assertEqual(server.lastTransitionTime, started, "same status, same transition time")
        self.assertEqual((server.reason, server.message), ("ImagePullBackOff", "the image can't be pulled"))
        state.set_condition(SERVER, TRUE, "Ready")
        assert server.lastTransitionTime is not None and started is not None
        self.assertGreaterEqual(server.lastTransitionTime, started)
        self.assertEqual(server.status, TRUE)
        self.assertIs(state.condition(INDEX), index)

    def test_backoff(self):
        """Test that the wait is the check interval, and doubles with each error in a row, up to its maximum."""
        state = VectorstoreDeploymentState.start()
        self.assertEqual(state.backoff(), DEPLOY_CHECK_INTERVAL)
        waits = []
        for errors in range(1, 7):
            state.consecutiveErrors = errors
            waits.append(state.backoff())
        self.assertEqual(waits, [30, 60, 120, 240, DEPLOY_MAX_BACKOFF, DEPLOY_MAX_BACKOFF])

    def test_stalled(self):
        """Test that a deploy whose next check is long overdue has lost its task, and one that ended hasn't."""
        state = VectorstoreDeploymentState.start()
        now = timezone.now()
        state.nextRetryAt = now
        self.assertFalse(state.is_stalled(now + DEPLOY_STALLED_AFTER))
        self.assertTrue(state.is_stalled(now + DEPLOY_STALLED_AFTER + timedelta(seconds=1)))
        state.finishedAt = now
        self.assertFalse(state.is_stalled(now + timedelta(days=1)))
