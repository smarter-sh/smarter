"""All Django views for the OpenAI API app."""

from http import HTTPStatus

import openai
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from smarter.common.conf import settings
from smarter.common.const import (  # VALID_EMBEDDING_MODELS,
    VALID_CHAT_COMPLETION_MODELS,
    OpenAIObjectTypes,
)
from smarter.common.exceptions import EXCEPTION_MAP
from smarter.common.utils import (
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.lib.django.validators import (  # validate_embedding_request,
    validate_completion_request,
    validate_item,
)


openai.organization = settings.openai_api_organization
openai.api_key = settings.openai_api_key.get_secret_value()


# pylint: disable=too-many-locals
def handler(data: dict):
    """
    Main Lambda handler function.

    Responsible for processing incoming requests and invoking the appropriate
    OpenAI API endpoint based on the contents of the request.
    """
    try:
        openai_results = {}
        request_body = get_request_body(data=data)
        object_type, model, messages, input_text, temperature, max_tokens = parse_request(request_body)
        request_meta_data = request_meta_data_factory(model, object_type, temperature, max_tokens, input_text)

        match object_type:
            case OpenAIObjectTypes.ChatCompletion:
                # https://platform.openai.com/docs/guides/gpt/chat-completions-api
                validate_item(
                    item=model,
                    valid_items=VALID_CHAT_COMPLETION_MODELS,
                    item_type="ChatCompletion models",
                )
                validate_completion_request(request_body)
                openai_results = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                openai_results = openai_results.model_dump()

            case OpenAIObjectTypes.Embedding:
                # https://platform.openai.com/docs/guides/embeddings/embeddings
                raise NotImplementedError("Refactoring of Embedding API v1 is in progress.")
                # validate_item(
                #     item=model,
                #     valid_items=VALID_EMBEDDING_MODELS,
                #     item_type="Embedding models",
                # )
                # validate_embedding_request(request_body)
                # openai_results = openai.Embedding.create(input=input_text, model=model)

            case OpenAIObjectTypes.Image:
                # https://platform.openai.com/docs/guides/images
                raise NotImplementedError("Refactoring of Image API v1 is in progress.")
                # n = request_body.get("n", settings.openai_endpoint_image_n)  # pylint: disable=invalid-name
                # size = request_body.get("size", settings.openai_endpoint_image_size)
                # return openai.Image.create(prompt=input_text, n=n, size=size)

            case OpenAIObjectTypes.Moderation:
                # https://platform.openai.com/docs/guides/moderation
                raise NotImplementedError("Refactoring of Moderation API v1 is in progress.")
                # openai_results = openai.Moderation.create(input=input_text)

            case OpenAIObjectTypes.Models:
                raise NotImplementedError("Refactoring of Models API v1 is in progress.")
                # openai_results = openai.Model.retrieve(model) if model else openai.Model.list()

            case OpenAIObjectTypes.Audio:
                raise NotImplementedError("Audio support is coming soon")

    # handle anything that went wrong
    # pylint: disable=broad-exception-caught
    except Exception as e:
        status_code, _message = EXCEPTION_MAP.get(type(e), (500, "Internal server error"))
        return http_response_factory(status_code=status_code, body=exception_response_factory(e))

    # success!! return the results
    return http_response_factory(
        status_code=HTTPStatus.OK,
        body={**openai_results, **request_meta_data},
    )


class OpenAIViewSet(viewsets.ViewSet):
    """top-level viewset for openai api requests"""

    permission_classes = [permissions.AllowAny]  # change this line

    # pylint: disable=W0613
    def create(self, request):
        """override the create method to handle POST requests."""
        return Response(handler(data=request.data))
