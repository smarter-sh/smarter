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

# smarter apps
from smarter.apps.api.api_admin import urls as api_admin_urls
from smarter.apps.api.hello_world import urls as hello_world_urls

# system urls
urlpatterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += api_admin_urls.urlpatterns

# application urls
urlpatterns += [
    # django admin console
    path("admin/", admin.site.urls),


    # all v0 endpoints belong here.
    # ----------------------------
    path("v0/", include((hello_world_urls, 'hello_world'), namespace='v0')),
]
