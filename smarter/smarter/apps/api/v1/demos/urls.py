"""
URL configuration for the api's demo end points, ``/api/v1/demos/``.

These serve the fictional data that the platform's example resources query, e.g. the
Stackademy course catalogue of the Stackademy ApiPlugin.
"""

from django.urls import path

from .const import namespace
from .views.stackademy import StackademyCourseCatalogueView

app_name = namespace


class ApiV1DemoUrls:
    """API v1 demo URLs configuration."""

    namespace = f"api:v1:{namespace}:"

    STACKADEMY_COURSE_CATALOGUE = "stackademy_course_catalogue"


# /api/v1/demos/ is the main entry point
urlpatterns = [
    path(
        "stackademy/course-catalogue/",
        StackademyCourseCatalogueView.as_view(),
        name=ApiV1DemoUrls.STACKADEMY_COURSE_CATALOGUE,
    ),
]
