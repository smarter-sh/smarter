"""Test :mod:`smarter.apps.vectorstore.execution`: a managed vector database's operations, through the tool runner (issue #1081)."""

from unittest.mock import MagicMock, patch

from httpx import Headers
from pinecone.exceptions import ForbiddenException, UnauthorizedException
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from smarter.apps.llmtool.runner import (
    ToolCall,
    ToolCallResult,
    call_model_for,
    executor_for,
)
from smarter.apps.vectorstore.backends.base import (
    VectorStoreBackendConnectionError,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendRejectedError,
    json_dict,
    json_dicts,
)
from smarter.apps.vectorstore.execution import (
    CONNECTION_STATUS,
    CREDENTIALS_STATUS,
    REJECTED_STATUS,
    VECTORSTORE_TOOL_CALL_KIND,
    VectorstoreToolCall,
    client_for,
    execute_vectorstore_call,
    run_in_process,
    run_vectorstore_operation,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

RUNNER_PATCH = "smarter.apps.vectorstore.execution.get_tool_runner"
CLIENT_PATCH = "smarter.apps.vectorstore.execution.client_for"
API_KEY = "test-vectorstore-api-key"


def call(
    operation: str, params=None, backend: str = "qdrant", url: str = "https://qdrant.example.com:6333"
) -> VectorstoreToolCall:
    """A resolved operation on the test collection."""
    return VectorstoreToolCall(
        backend=backend,  # type: ignore[arg-type]
        url=url,
        api_key=API_KEY,
        index_name="test_collection",
        operation=operation,
        params=params or {},
    )


class TestVectorstoreToolCall(SmarterTestBase):
    """The call travels as JSON, without its api key in repr(), and the runner knows its kind."""

    def test_call_travels_as_json(self):
        resolved = call("upsert", {"ids": ["a"], "vectors": [[0.1, 0.2]], "texts": ["t"], "metadatas": [{}]})
        rebuilt = VectorstoreToolCall.model_validate_json(resolved.model_dump_json())
        self.assertEqual(rebuilt, resolved)
        self.assertNotIn(API_KEY, repr(resolved))

    def test_the_runner_knows_the_kind(self):
        self.assertIs(executor_for(VECTORSTORE_TOOL_CALL_KIND), execute_vectorstore_call)
        self.assertIs(call_model_for(VECTORSTORE_TOOL_CALL_KIND), VectorstoreToolCall)

    def test_executor_needs_a_vectorstore_call(self):
        with self.assertRaises(TypeError):
            execute_vectorstore_call(ToolCall(kind="other"))


class TestQdrantOperations(SmarterTestBase):
    """Qdrant's operations, against an in-memory Qdrant, as the tool worker runs them."""

    def setUp(self):
        super().setUp()
        self.client = QdrantClient(location=":memory:")
        patcher = patch(CLIENT_PATCH, return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_operation(self, operation: str, params=None) -> ToolCallResult:
        return execute_vectorstore_call(call(operation, params))

    def vector_count(self) -> int:
        return json_dict(self.run_operation("stats").value)["vector_count"]

    def test_a_collections_life(self):
        """Create, upsert, query (with a filter, a threshold and vectors), delete a document, drop."""
        self.assertEqual(self.run_operation("exists").value, False)
        self.run_operation("create", {"dimension": 2, "metric": "cosine"})
        self.assertEqual(self.run_operation("exists").value, True)
        upsert = {
            "ids": [
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ],
            "vectors": [[1.0, 0.0], [0.0, 1.0]],
            "texts": ["east", "north"],
            "metadatas": [{"document_id": 1, "team": "a"}, {"document_id": 2, "team": "b"}],
        }
        self.assertIsNone(self.run_operation("upsert", upsert).failure)
        matches = json_dicts(self.run_operation("query", {"vector": [1.0, 0.0], "limit": 2}).value)
        self.assertEqual([match["text"] for match in matches], ["east", "north"])
        self.assertEqual(matches[0]["metadata"], {"document_id": 1, "team": "a"})
        self.assertNotIn("vector", matches[0])
        filtered = json_dicts(
            self.run_operation("query", {"vector": [1.0, 0.0], "limit": 2, "filter": {"team": "b"}}).value
        )
        self.assertEqual([match["text"] for match in filtered], ["north"])
        above = json_dicts(
            self.run_operation("query", {"vector": [1.0, 0.0], "limit": 2, "score_threshold": 0.5}).value
        )
        self.assertEqual(len(above), 1)
        with_vectors = json_dicts(
            self.run_operation("query", {"vector": [1.0, 0.0], "limit": 1, "with_vectors": True}).value
        )
        self.assertEqual(len(with_vectors[0]["vector"]), 2)
        self.assertEqual(self.vector_count(), 2)
        self.run_operation("delete_document", {"document_id": 1})
        self.assertEqual(self.vector_count(), 1)
        self.run_operation("delete", {"ids": ["00000000-0000-0000-0000-000000000002"]})
        self.assertEqual(self.vector_count(), 0)
        self.run_operation("drop")
        self.assertEqual(self.run_operation("exists").value, False)

    def test_an_unknown_operation(self):
        result = self.run_operation("rm_rf")
        self.assertIsNotNone(result.failure)
        self.assertEqual(result.status_code, CONNECTION_STATUS)


class TestErrors(SmarterTestBase):
    """A failure keeps its class on its way back from the tool worker."""

    def test_errors_become_statuses(self):
        cases = (
            ("qdrant", UnexpectedResponse(401, "Unauthorized", b"", Headers()), CREDENTIALS_STATUS),
            ("qdrant", UnexpectedResponse(500, "Server Error", b"", Headers()), CONNECTION_STATUS),
            ("qdrant", ConnectionError("reset"), CONNECTION_STATUS),
            ("pinecone", UnauthorizedException("Invalid API key"), CREDENTIALS_STATUS),
            ("pinecone", ForbiddenException("Quota exceeded"), REJECTED_STATUS),
        )
        for backend, error, status in cases:
            with self.subTest(backend=backend, error=error):
                client = MagicMock()
                client.collection_exists.side_effect = error
                client.has_index.side_effect = error
                with patch(CLIENT_PATCH, return_value=client):
                    result = execute_vectorstore_call(call("exists", backend=backend))
                self.assertIsNotNone(result.failure)
                self.assertEqual(result.status_code, status)

    def test_statuses_become_errors(self):
        """The app raises the same class of error as the in-process path would."""
        cases = (
            (CREDENTIALS_STATUS, VectorStoreBackendCredentialsError),
            (REJECTED_STATUS, VectorStoreBackendRejectedError),
            (CONNECTION_STATUS, VectorStoreBackendConnectionError),
            (None, VectorStoreBackendConnectionError),
        )
        for status, expected in cases:
            with self.subTest(status=status):
                runner = MagicMock()
                runner.run.return_value = ToolCallResult(failure="it failed", status_code=status)
                with patch(RUNNER_PATCH, return_value=runner), self.assertRaises(expected):
                    run_vectorstore_operation(
                        "qdrant", "exists", index_name="test_collection", url="https://q.example.com"
                    )

    def test_in_process_errors_are_classified_too(self):
        client = MagicMock()
        client.collection_exists.side_effect = UnexpectedResponse(403, "Forbidden", b"", Headers())
        with self.assertRaises(VectorStoreBackendCredentialsError):
            run_in_process("qdrant", client, "test_collection", "exists", {})


class TestDestinations(SmarterTestBase):
    """The tool worker connects only to a public address, and only with a key where one is needed."""

    def test_a_private_or_link_local_url_is_refused(self):
        for url in ("http://10.0.0.5:6333", "http://169.254.169.254/", "https://192.168.1.10:6333"):
            with self.subTest(url=url):
                result = execute_vectorstore_call(call("exists", url=url))
                self.assertEqual(result.status_code, REJECTED_STATUS)
                self.assertIn("not permitted", result.failure or "")

    def test_a_public_url_on_qdrant_clouds_port(self):
        """Qdrant Cloud's port, 6333, is permitted, and the client gets the url and the key."""
        with (
            patch("smarter.apps.vectorstore.execution.safe_http.validate_destination_url") as validate,
            patch("smarter.apps.vectorstore.execution.QdrantClient") as qdrant,
        ):
            client_for(call("exists", url="https://xyz.cloud.qdrant.io:6333"))
        validate.assert_called_once_with("https://xyz.cloud.qdrant.io:6333", require_https=False)
        qdrant.assert_called_once_with(url="https://xyz.cloud.qdrant.io:6333", api_key=API_KEY, timeout=30)

    def test_pinecone_needs_a_key(self):
        resolved = call("exists", backend="pinecone", url="").model_copy(update={"api_key": ""})
        result = execute_vectorstore_call(resolved)
        self.assertEqual(result.status_code, CREDENTIALS_STATUS)


class TestThroughTheRunner(SmarterTestBase):
    """Without a client, an operation goes to the runner, and nothing connects in this process."""

    def test_a_managed_operation_goes_to_the_runner(self):
        runner = MagicMock()
        runner.run.return_value = ToolCallResult(value={"vector_count": 3})
        with (
            patch(RUNNER_PATCH, return_value=runner),
            patch("smarter.apps.vectorstore.execution.QdrantClient") as qdrant,
            patch("smarter.apps.vectorstore.execution.Pinecone") as pinecone,
        ):
            value = run_vectorstore_operation(
                "qdrant", "stats", index_name="test_collection", url="https://q.example.com", api_key=API_KEY
            )
        self.assertEqual(value, {"vector_count": 3})
        qdrant.assert_not_called()
        pinecone.assert_not_called()
        sent = runner.run.call_args.args[0]
        self.assertEqual((sent.operation, sent.url, sent.api_key), ("stats", "https://q.example.com", API_KEY))

    def test_a_client_runs_in_process(self):
        """A self-hosted server's client, or a test's, runs the operation here, and the runner isn't used."""
        client = MagicMock()
        client.collection_exists.return_value = True
        with patch(RUNNER_PATCH) as get_runner:
            self.assertTrue(run_vectorstore_operation("qdrant", "exists", index_name="test_collection", client=client))
        get_runner.assert_not_called()
