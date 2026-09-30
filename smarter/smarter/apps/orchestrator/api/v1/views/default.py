# pylint: disable=W0611
"""Smarter Orchestrator API view."""

import traceback
from http import HTTPStatus

from django.http import JsonResponse

from smarter.apps.orchestrator.models import Orchestrator
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base import OrchestratorApiBaseViewSet

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


class DefaultOrchestratorApiView(OrchestratorApiBaseViewSet):
    """
    Main view for Smarter Orchestrator API prompt prompts.

    top-level viewset for customer-deployed Plugin-based Prompt APIs.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Smarter API Orchestrator dispatch method.

        :param request: Django HttpRequest object
        :param args: Additional positional arguments
        :param name: Orchestrator name (str, optional)
        :param kwargs: Additional keyword arguments

        **Example request payload**:

        .. code-block:: json

           {
               "session_key": "dde3dde5e3b97134f5bce5edf26ec05134da71d8485a86dfc9231149aaf0b0af",
               "messages": [
                   {
                       "role": "assistant",
                       "content": "Welcome to Smarter!.  how can I assist you today?"
                   },
                   {
                       "role": "user",
                       "content": "Hello, World!"
                   }
               ]
           }
        """
        hashed_id = kwargs.pop("hashed_id", None)
        if hashed_id:
            self._orchestrator_id = Orchestrator.id_from_hashed_id(hashed_id)
        else:
            self._orchestrator_id = kwargs.pop("orchestrator_id", None)
        self._name = kwargs.pop("name", None)
        logger.info("%s - dispatch() %s %s ", self.formatted_class_name, self.orchestrator, self.user_profile)

        try:
            retval = super().dispatch(request, *args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            err_traceback = traceback.format_exc()
            logger.error("DefaultOrchestratorApiView.dispatch: %s, %s", e, err_traceback)
            retval = JsonResponse(
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                data={
                    "error": "An error occurred while processing your request.",
                    "details": str(e),
                    "trace": err_traceback,
                },
            )
        return retval
