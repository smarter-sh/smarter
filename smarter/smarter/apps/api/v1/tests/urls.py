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
)


app_name = namespace

# /api/v1/tests/ is the main entry point
urlpatterns = [
    path("unauthenticated/dict/", TestJsonDictView.as_view(), name="test_json_dict_unauthenticated"),
    path("unauthenticated/list/", TestJsonListView.as_view(), name="test_json_list_unauthenticated"),
    path("authenticated/dict/", TestJsonDictViewAuthenticated.as_view(), name="test_json_dict_authenticated"),
    path("authenticated/list/", TestJsonListViewAuthenticated.as_view(), name="test_json_list_authenticated"),
]
