"""URL configuration for the drop zone manifest apply API end point."""

from django.urls import path

from smarter.apps.api.v1.cli.views.apply import ApiV1CliApplyApiView
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .const import namespace

logger = logging.getLogger(__name__)

app_name = namespace


class DropzoneApiReverseNames:
    """
    A class to hold the names of the dropzone views for easy reference.

    throughout the codebase.
    """

    namespace = namespace

    dropzone = to_snake_case(ApiV1CliApplyApiView.__name__)


urlpatterns = [
    path("apply/", ApiV1CliApplyApiView.as_view(), name=DropzoneApiReverseNames.dropzone),
]
