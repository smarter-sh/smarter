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

from django.urls import include, path


# /api/v1/ is the main entry point for the API
urlpatterns = [
    # chatbots: the url is of the form https://example.3141-5926-5359.alpha.api.smarter.sh
    path("", include("smarter.apps.chatbot.api.v1.urls")),
    # smarter resources:
    path("account/", include("smarter.apps.account.api.v1.urls")),
    path("chatbots/", include("smarter.apps.chatbot.api.v1.urls")),
    path("chat/", include("smarter.apps.chat.api.v1.urls")),
    path("plugins/", include("smarter.apps.plugin.api.v1.urls")),
    # /api/v1/cli/ is used for the command-line interface
    path("cli/", include("smarter.apps.api.v1.cli.urls")),
    # /api/v1/cli/tests is used for unit tests
    path("tests/", include("smarter.apps.api.v1.tests.urls")),
]

# for backward compatibility prior to 0.7.2
urlpatterns += [
    path("chatbot/", include("smarter.apps.chatbot.api.v1.urls")),
]
