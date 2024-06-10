"""URL configuration for dashboard legal pages."""

from django.conf import settings
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .views import (
    DeveloperDocsArchitectureView,
    DeveloperDocsChatBotApiView,
    DeveloperDocsCliView,
    DeveloperDocsDjangoReactView,
    DeveloperDocsGoodCodoingPracticeView,
    DeveloperDocsOpenAIGettingStartedView,
    DeveloperDocsSemanticVersioningView,
    DeveloperDocsTwelveFactorView,
    DocsView,
    SiteMapView,
)


schema_view = get_schema_view(
    openapi.Info(
        title=settings.SMARTER_API_NAME,
        default_version="v1",
        description=settings.SMARTER_API_DESCRIPTION,
        terms_of_service="https:/smarter.sh/tos/",
        contact=openapi.Contact(email="contact@smarter.sh"),
        license=openapi.License(name="AGPL-3.0 License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("", DocsView.as_view(), name="docs-home"),
    path("sitemap", SiteMapView.as_view(), name="sitemap"),
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^swagger/$", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    re_path(r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc-ui"),
    path("developer/12-factor/", DeveloperDocsTwelveFactorView.as_view(), name="developer-12-factor"),
    path("developer/architecture/", DeveloperDocsArchitectureView.as_view(), name="developer-architecture"),
    path("developer/chatbot-api/", DeveloperDocsChatBotApiView.as_view(), name="developer-chatbot-api"),
    path("developer/cli/", DeveloperDocsCliView.as_view(), name="developer-cli"),
    path("developer/django-react/", DeveloperDocsDjangoReactView.as_view(), name="developer-django-react"),
    path(
        "developer/good-coding-practice/",
        DeveloperDocsGoodCodoingPracticeView.as_view(),
        name="developer-good-coding-practice",
    ),
    path(
        "developer/openai-getting-started/",
        DeveloperDocsOpenAIGettingStartedView.as_view(),
        name="developer-openai-getting-started",
    ),
    path(
        "developer/semantic-versioning/",
        DeveloperDocsSemanticVersioningView.as_view(),
        name="developer-semantic-versioning",
    ),
]
