"""
URL configuration for smarter test end points.
"""

from django.urls import path

from .const import namespace
from .views.test_views import (
    TestJsonDictView,
    TestJsonDictViewAuthenticated,
    TestJsonListView,
    TestJsonListViewAuthenticated,
    TestStackademyCourseCatalogueView,
)

app_name = namespace


class ApiV1TestUrls:
    """API v1 test URLs configuration."""

    namespace = f"api:v1:{namespace}:"

    UNAUTHENTICATED_DICT = "test_json_dict_unauthenticated"
    UNAUTHENTICATED_LIST = "test_json_list_unauthenticated"
    AUTHENTICATED_DICT = "test_json_dict_authenticated"
    AUTHENTICATED_LIST = "test_json_list_authenticated"
    STACKADEMY_COURSE_CATALOGUE = "stackademy_course_catalogue"


# /api/v1/tests/ is the main entry point
urlpatterns = [
    path("unauthenticated/dict/", TestJsonDictView.as_view(), name=ApiV1TestUrls.UNAUTHENTICATED_DICT),
    path("unauthenticated/list/", TestJsonListView.as_view(), name=ApiV1TestUrls.UNAUTHENTICATED_LIST),
    path("authenticated/dict/", TestJsonDictViewAuthenticated.as_view(), name=ApiV1TestUrls.AUTHENTICATED_DICT),
    path("authenticated/list/", TestJsonListViewAuthenticated.as_view(), name=ApiV1TestUrls.AUTHENTICATED_LIST),
    path(
        "stackademy/course-catalogue/",
        TestStackademyCourseCatalogueView.as_view(),
        name=ApiV1TestUrls.STACKADEMY_COURSE_CATALOGUE,
    ),
]
