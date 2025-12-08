CLI Error Handling
===================

Smarter API V1 CLI base view (see :py:class:`smarter.apps.api.v1.cli.views.base.CliBaseApiView`) implements a common
error handling mechanism in its
``dispatch`` method. This mechanism captures and maps exceptions to a finite set of
HTTP status codes, ensuring consistent error responses across the CLI API.

Error responses are returned in a structured JSON format using the
:class:`smarter.lib.journal.http.SmarterJournaledJsonErrorResponse` class,
which properly formats the error details for CLI client consumption.


.. code-block:: python

        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value

            if type(e) in (SAMBrokerErrorNotImplemented,):
                status = HTTPStatus.NOT_IMPLEMENTED.value
            elif type(e) in (SAMBrokerErrorNotReady,):
                status = HTTPStatus.SERVICE_UNAVAILABLE.value
            elif type(e) in (SAMBrokerErrorNotFound,):
                status = HTTPStatus.NOT_FOUND.value
            elif type(e) in (SAMBrokerReadOnlyError,):
                status = HTTPStatus.METHOD_NOT_ALLOWED.value
            elif type(e) in (
                SmarterAPIV1CLIViewErrorNotAuthenticated,
                SmarterInvalidApiKeyError,
                SmarterTokenError,
                NotAuthenticated,
                AuthenticationFailed,
                AttributeError,  # can be raised by a django admin decorator if request or request.user is None
            ):
                status = HTTPStatus.FORBIDDEN.value
            elif type(e) in (
                SAMBrokerError,
                SmarterValueError,
                SmarterIlligalInvocationError,
                SmarterBusinessRuleViolation,
            ):
                status = HTTPStatus.BAD_REQUEST.value
            elif type(e) in (
                SmarterChatappViewError,
                SmarterChatBotException,
                DocsError,
                SmarterPluginError,
                SmarterConfigurationError,
                SmarterAWSError,
                KubernetesHelperException,
                SmarterJournalEnumException,
                SmarterException,
            ):
                status = HTTPStatus.INTERNAL_SERVER_ERROR.value

            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=e,
                status=status,
                stack_trace=traceback.format_exc(),
            )
