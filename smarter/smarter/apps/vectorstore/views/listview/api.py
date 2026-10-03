# pylint: disable=W0613
"""The JSON API of the React Vectorstore list in the web console: list, clone, rename and delete."""

from http import HTTPStatus

from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.vectorstore.caching import (
    get_cached_vectorstores_available_to_user_profile,
    get_cached_vectorstores_owned_by_user_profile,
    get_cached_vectorstores_shared_with_user_profile,
    invalidate_all_cached_vectorstores_for_user_profile,
)
from smarter.apps.vectorstore.models import VectorstoreMeta, VectorstoreStatus
from smarter.apps.vectorstore.serializers import VectorstoreSerializer
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

DEFAULT_PAGE_SIZE = 25
STATE_FIELDS = {
    # what a clone does not copy: it is a new, undeployed vectorstore.
    "status": VectorstoreStatus.PENDING,
    "status_message": "",
    "index_name": "",
    "endpoint_url": "",
    "api_key_secret": None,
    "vector_count": 0,
    "stats": {},
    "deployed_at": None,
    "last_checked_at": None,
    "last_snapshot_at": None,
    "last_maintenance_at": None,
}

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])


class VectorstoreListApiView(SmarterAuthenticatedNeverCachedWebView):
    """The vectorstores that the user owns, those shared with them, or both."""

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        ownership_filter = kwargs.get("ownership_filter") or SmarterResourceOwnershipFilterEnum.ALL
        page = request.GET.get("page", 1)
        page_size = request.GET.get("page_size", DEFAULT_PAGE_SIZE)
        if request.GET.get("invalidate_cache", "false").lower() == "true":
            invalidate_all_cached_vectorstores_for_user_profile(user_profile=self.user_profile)  # type: ignore
        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            qs = get_cached_vectorstores_owned_by_user_profile(user_profile=self.user_profile)  # type: ignore
        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            qs = get_cached_vectorstores_shared_with_user_profile(user_profile=self.user_profile)  # type: ignore
        elif ownership_filter == SmarterResourceOwnershipFilterEnum.ALL:
            qs = get_cached_vectorstores_available_to_user_profile(user_profile=self.user_profile)  # type: ignore
        else:
            return JsonResponse(
                {"error": "Invalid ownership_filter. Must be one of 'owned', 'shared', or 'all'."},
                status=HTTPStatus.BAD_REQUEST,
            )
        vectorstores = Paginator(qs.order_by("-updated_at"), page_size).get_page(page)
        return JsonResponse(
            {
                "user": UserProfileSerializer(self.user_profile).data,
                "admin": UserProfileSerializer(smarter_cached_objects.smarter_admin_user_profile).data,
                "objects": VectorstoreSerializer(vectorstores, many=True, context={"request": request}).data,
            }
        )


class VectorstoreListApiCloneView(SmarterAuthenticatedNeverCachedWebView):
    """
    Clone a vectorstore: a new, undeployed vectorstore with the same spec, owned by the user.

    Its documents and database are not copied. Deploy it, and add documents, to use it.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        vectorstore_id = kwargs.get("vectorstore_id")
        new_name = self.to_snake_case(str(kwargs.get("new_name") or "").strip())
        if not new_name:
            return JsonResponse({"error": "new_name is required."}, status=HTTPStatus.BAD_REQUEST)
        source = (
            VectorstoreMeta.objects.with_read_permission_for(self.user_profile.user)  # type: ignore
            .filter(id=vectorstore_id)
            .first()
        )
        if source is None:
            return JsonResponse({"error": f"Vectorstore {vectorstore_id} not found."}, status=HTTPStatus.NOT_FOUND)
        if VectorstoreMeta.objects.filter(user_profile=self.user_profile, name=new_name).exists():
            return JsonResponse(
                {"error": f"You already have a vectorstore named {new_name}."}, status=HTTPStatus.CONFLICT
            )
        with transaction.atomic():
            clone = VectorstoreMeta.objects.get(pk=source.pk)
            clone.pk = None
            clone.id = None
            clone.name = new_name
            clone.user_profile = self.user_profile
            for field, value in STATE_FIELDS.items():
                setattr(clone, field, value)
            spec = dict(clone.spec or {})
            spec.setdefault("index", {}).pop("name", None)
            clone.spec = spec
            clone.save()
            clone.tags.set(source.tags_list)
        invalidate_all_cached_vectorstores_for_user_profile(user_profile=self.user_profile)  # type: ignore
        return JsonResponse(VectorstoreSerializer(clone, context={"request": request}).data, status=HTTPStatus.OK)


class VectorstoreListApiDeleteView(SmarterAuthenticatedNeverCachedWebView):
    """Destroy a vectorstore's database and data, unless deletionProtection is enabled, then delete it."""

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        vectorstore_id = kwargs.get("vectorstore_id")
        vectorstore = (
            VectorstoreMeta.objects.with_ownership_permission_for(self.user_profile.user)  # type: ignore
            .filter(id=vectorstore_id)
            .first()
        )
        if vectorstore is None:
            return JsonResponse({"error": f"Vectorstore {vectorstore_id} not found."}, status=HTTPStatus.NOT_FOUND)
        try:
            service = VectorstoreService(vectorstore)
            if vectorstore.deployed_at or vectorstore.deletion_protection:
                service.destroy()
            secret = vectorstore.api_key_secret
            vectorstore.delete()
            if secret is not None:
                secret.delete()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("%s.post() failed to delete %s: %s", self.formatted_class_name, vectorstore, e)
            return JsonResponse({"error": str(e)}, status=HTTPStatus.BAD_REQUEST)
        invalidate_all_cached_vectorstores_for_user_profile(user_profile=self.user_profile)  # type: ignore
        return JsonResponse({"message": f"Vectorstore {vectorstore_id} deleted."}, status=HTTPStatus.OK)


class VectorstoreListApiRenameView(SmarterAuthenticatedNeverCachedWebView):
    """Rename a vectorstore.

    Its database keeps its index name, and its server its Kubernetes name.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        vectorstore_id = kwargs.get("vectorstore_id")
        new_name = self.to_snake_case(str(kwargs.get("new_name") or "").strip())
        if not new_name:
            return JsonResponse({"error": "new_name is required."}, status=HTTPStatus.BAD_REQUEST)
        vectorstore = (
            VectorstoreMeta.objects.with_ownership_permission_for(self.user_profile.user)  # type: ignore
            .filter(id=vectorstore_id)
            .first()
        )
        if vectorstore is None:
            return JsonResponse({"error": f"Vectorstore {vectorstore_id} not found."}, status=HTTPStatus.NOT_FOUND)
        if VectorstoreMeta.objects.filter(user_profile=vectorstore.user_profile, name=new_name).exists():
            return JsonResponse({"error": f"A vectorstore named {new_name} exists."}, status=HTTPStatus.CONFLICT)
        vectorstore.rename(new_name=new_name)
        invalidate_all_cached_vectorstores_for_user_profile(user_profile=self.user_profile)  # type: ignore
        return JsonResponse(VectorstoreSerializer(vectorstore, context={"request": request}).data, status=HTTPStatus.OK)
