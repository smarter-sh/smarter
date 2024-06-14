"""Django context processors for docs/base.html"""

import logging

from smarter.__version__ import __version__
from smarter.common.conf import settings as smarter_settings


logger = logging.getLogger(__name__)


# pylint: disable=W0613
def base(request):
    """Base context processor for templates that inherit from docs/base.html"""
    docs_context = {
        "smarter_version": "v" + __version__,
        "smarter_marketing_site_url": smarter_settings.marketing_site_url,
    }
    return docs_context
