"""Account urls for smarter api"""

from django.urls import path

from smarter.apps.secret.api.v1.views import SecretListView, SecretView
from smarter.apps.secret.const import namespace

app_name = namespace

urlpatterns = [
    path("", SecretListView.as_view(), name="secret_list_view"),
    path("<int:secret_id>/", SecretView.as_view(), name="secret_view"),
]
