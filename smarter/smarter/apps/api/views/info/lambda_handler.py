# -*- coding: utf-8 -*-
# pylint: disable=R0911,R0912,W0718
"""Lambda entry point for /info"""

from smarter.apps.common.aws import aws_infrastructure_config as aws_config
from smarter.apps.common.conf import settings
from smarter.apps.common.utils import http_response_factory


# pylint: disable=unused-argument
def handler(event, context):  # noqa: C901
    """Lambda entry point"""
    info = {
        "aws": aws_config.dump,
        "settings": settings.dump,
    }
    return http_response_factory(status_code=200, body=info)
