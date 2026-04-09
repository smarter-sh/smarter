"""
URL configuration for the vectorstore app.
"""

from django.urls import include, path

from smarter.apps.vectorstore.api import urls as api_urls
from smarter.apps.vectorstore.views.vectorstores import (
    VectorstoreListView,
    VectorstoreManifestView,
)
from smarter.common.utils import camel_to_snake

from .api.const import namespace as api_namespace
from .const import namespace

app_name = namespace


class VectorstoreReverseViews:
    """
    Reverse views for the Vectorstore app.
    Provides named references for reversing Vectorstore-related API endpoints.

    This class is used for reverse URL resolution in Django, where each attribute
    corresponds to a Vectorstore command endpoint. The names are derived from the actual
    API view class names, ensuring consistency and reducing the risk of typos
    when using Django's URL reversing features.

    All Vectorstore endpoints in the Smarter platform are included as attributes
    of this class. This centralizes the reverse URL names for all Vectorstore endpoints,
    making it easier to maintain and reference them throughout the codebase.

    Usage
    -----
    Use these attributes with Django's ``reverse()`` function or in templates
    to generate URLs for Vectorstore API endpoints based on the view class names.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(VectorstoreReverseViews.describe, kwargs={'hashed_id': 'rMTAwMDAzOQx'})

        # returns manifest of the chatbot with the given hashed_id
        retval = VectorstoreReverseViews.describe
        print(retval)

    """

    namespace = namespace

    @staticmethod
    def camel_case(obj) -> str:
        """
        Convert CamelCase to snake_case for URL naming.

        :param name: The CamelCase string to convert.
        :return: The converted snake_case string.
        :rtype: str
        """
        return str(camel_to_snake(obj.__name__))

    vectorstore_detail = camel_case(VectorstoreManifestView)
    vectorstore_list = camel_case(VectorstoreListView)


urlpatterns = [
    path("", VectorstoreListView.as_view(), name="listview"),
    path("api/", include(api_urls, namespace=api_namespace)),
    path(
        "vectorstores/<str:name>/<str:backend>/manifest/",
        VectorstoreManifestView.as_view(),
        name=VectorstoreReverseViews.vectorstore_detail,
    ),
]
