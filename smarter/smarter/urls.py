# -*- coding: utf-8 -*-
"""
URL configuration for smarter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from smarter.apps.api.views.views import LogoutView, custom_api_root


urlpatterns = [
    path("", custom_api_root, name="custom_api_root"),
    path("api-auth/logout/", LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("admin/", admin.site.urls),
    path("hello-world/", include("smarter.apps.hello_world.urls")),
    path("v0/", include("smarter.apps.api.v0_urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
