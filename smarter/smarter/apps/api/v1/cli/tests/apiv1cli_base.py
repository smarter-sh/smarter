"""Base class for testing Api v1 CLI commands"""

from abc import ABC, abstractmethod

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase


class ApiV1CliTestBase(ABC, ApiV1TestBase):
    """Base class for testing Api v1 CLI commands"""

    @abstractmethod
    def test_apply(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_describe(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_delete(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_deploy(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_example_manifest(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_get(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_logs(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def test_undeploy(self) -> None:
        raise NotImplementedError
