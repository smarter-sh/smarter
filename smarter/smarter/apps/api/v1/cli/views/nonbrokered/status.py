# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view."""

import platform
from http import HTTPStatus

from django_redis import get_redis_connection

from smarter.apps.api.v1.cli.views.base import CliBaseApiView
from smarter.apps.api.v1.contract.models import (
    CliApiStatus,
    CliApiStatusCompute,
    CliApiStatusInfrastructures,
    CliApiStatusRedis,
)
from smarter.apps.infrastructure.exceptions import SmarterInfrastructureError
from smarter.apps.infrastructure.services import infrastructure
from smarter.lib import logging
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)


class ApiV1CliStatusApiView(CliBaseApiView):
    """Smarter API command-line interface 'status' view."""

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliStatusApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def get_kubernetes_info(self) -> SmarterDictType:
        """
        Return Kubernetes cluster information.

        Without cloud credentials there is no cluster to report on, so the
        status shows the error instead of the whole status request failing.

        :return: Kubernetes cluster information, or {"error": ...} if the cloud provider is not ready
        :rtype: dict
        """
        try:
            return infrastructure.provider.get_kubernetes_cluster_info()
        except SmarterInfrastructureError as e:
            logger.warning("%s.get_kubernetes_info() %s", self.formatted_class_name, e)
            return {"error": str(e)}

    def get_redis_info(self):
        """
        Return Redis server information.

        :return: Redis server information
        :rtype: dict
        """
        logger.debug("%s.get_redis_info() called", self.formatted_class_name)

        client = get_redis_connection("default")
        info = client.info()
        retval = {
            "gcc_version": info.get("gcc_version"),
            "os": info.get("os"),
            "redis_build_id": info.get("redis_build_id"),
            "redis_version": info.get("redis_version"),
        }
        return retval

    def status(self):
        """Get status information about the Smarter platform."""

        logger.debug("%s.status() called", self.formatted_class_name)

        status = CliApiStatus(
            infrastructures=CliApiStatusInfrastructures(
                kubernetes=self.get_kubernetes_info(),
                redis=CliApiStatusRedis(**self.get_redis_info()),
            ),
            compute=CliApiStatusCompute(
                machine=platform.machine(),
                release=platform.release(),
                platform=platform.platform(aliased=True),
                processor=platform.processor(),
                system=platform.system(),
                version=platform.version(),
            ),
        )
        data = {SmarterJournalApiResponseKeys.DATA: status.model_dump(mode="json")}
        return SmarterJournaledJsonResponse(
            self.request,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.STATUS),
            data=data,
            status=HTTPStatus.OK.value,
        )

    def post(self, request):
        """ApiV1CliStatusApiView post view."""
        response = self.status()
        return response
