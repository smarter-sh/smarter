"""Django context processors for docs/base.html"""

from smarter.__version__ import __version__
from smarter.common.conf import settings as smarter_settings


# pylint: disable=W0613
def base(request):
    """Base context processor for templates that inherit from docs/base.html"""
    if (
        request
        and hasattr(request, "user")
        and hasattr(request.user, "is_authenticated")
        and request.user.is_authenticated
    ):
        smarter_home_url = "/"
    else:
        smarter_home_url = smarter_settings.marketing_site_url
    docs_context = {
        "smarter_version": "v" + __version__,
        "smarter_marketing_site_url": smarter_settings.marketing_site_url,
        "smarter_home_url": smarter_home_url,
        "smarter_logo": smarter_settings.logo,
    }
    return docs_context
