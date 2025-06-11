"""
Django URL patterns for the chatapp

how we got here:
 - /
 - /workbench/<str:name>/config/
 - also via smarter.urls.py config_redirector() ???

"""

from .api.const import namespace as api_namespace
from .const import namespace


app_name = namespace

urlpatterns = []
