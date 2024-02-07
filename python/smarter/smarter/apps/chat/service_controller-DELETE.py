# -*- coding: utf-8 -*-
"""
Kubernetes Service Controller. This is only used for Kubernetes based deployments. This provides a
way to package all four Lambdas into a single Docker container deployed as a single Kubernetes pod.
"""

import json
import logging

from openai_api.lambda_info.lambda_handler import handler as lambda_info_handler
from openai_api.lambda_langchain.lambda_handler import handler as lambda_langchain_handler
from openai_api.lambda_openai_function.lambda_handler import handler as lambda_openai_function_handler
from openai_api.lambda_openai_v2.lambda_handler import handler as lambda_openai_v2_handler

LAMBDA_HANDLERS = {
    "lambda_info": lambda_info_handler,
    "lambda_langchain": lambda_langchain_handler,
    "lambda_openai_function": lambda_openai_function_handler,
    "lambda_openai_v2": lambda_openai_v2_handler,
}

log = logging.getLogger(__name__)

def handler(event, context):
    """Passes the event to the appropriate handler based on the python_handler key in the event"""
    python_handler = event.get("python_handler", "python_handler_undefined")
    if python_handler not in LAMBDA_HANDLERS:
        raise ValueError("python_handler is required")

    log.info("python_handler: %s", python_handler)
    log.info("event: %s", json.dumps(event, indent=4))

    return LAMBDA_HANDLERS[python_handler](event, context)
