"""Views for the authenticated user's profile image."""

from http import HTTPStatus

from django import forms, http
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_avatar_url
from smarter.lib import logging
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])

PROFILE_IMAGE_MAX_BYTES = 2 * 1024 * 1024
"""The largest profile image that a user may upload, 2 MiB."""

PROFILE_IMAGE_CONTENT_TYPES = ("image/png", "image/jpeg", "image/gif", "image/webp")
"""The image formats that a user may upload.

SVG is excluded because it can carry script.
"""


class ProfileImageForm(forms.ModelForm):
    """Form for uploading a :attr:`UserProfile.profile_image`, validated as an image by Pillow."""

    class Meta:
        """Meta class for ProfileImageForm."""

        model = UserProfile
        fields = ["profile_image"]

    def clean_profile_image(self):
        """
        Require an image of an allowed format and size.

        :returns: The uploaded file.
        :raises forms.ValidationError: If no file was sent, or it is too large, or of a format that isn't allowed.
        """
        image = self.cleaned_data.get("profile_image")
        if not image or "profile_image" not in self.files:
            raise forms.ValidationError(_("Choose an image to upload."))
        if image.size > PROFILE_IMAGE_MAX_BYTES:
            raise forms.ValidationError(_("The image must be 2 MB or smaller."))
        if getattr(image, "content_type", None) not in PROFILE_IMAGE_CONTENT_TYPES:
            raise forms.ValidationError(_("The image must be a PNG, JPEG, GIF or WebP file."))
        return image


class ProfileImageView(SmarterAuthenticatedNeverCachedWebView):
    """
    Upload or remove the authenticated user's own profile image.

    ``POST`` a multipart form with a ``profile_image`` file to upload one, which
    replaces any earlier upload. ``DELETE`` removes it, and the console falls back
    to the image from the oauth provider, if any, else the default profile image.
    Both respond with JSON: ``{"profile_image_url": <url now shown>}`` on success,
    or the form's errors with status 400.
    """

    def own_user_profile(self, request) -> UserProfile:
        """
        Return the authenticated user's UserProfile, fresh from the database, since it is saved.

        The view's setup has already refused a user without one.

        :param request: The request, whose user owns the profile image.
        :returns: The UserProfile.
        """
        return UserProfile.objects.filter(user=request.user).order_by("-pk").first()  # type: ignore[return-value]

    def _response(self, request, user_profile: UserProfile) -> http.JsonResponse:
        UserProfile.get_cached_object(invalidate=True, user=request.user, account=user_profile.account)
        url = get_cached_avatar_url(user_id=request.user.id, invalidate=True)
        return http.JsonResponse(status=HTTPStatus.OK.value, data={"profile_image_url": url})

    def post(self, request, *args, **kwargs):
        user_profile = self.own_user_profile(request)
        previous = user_profile.profile_image.name if user_profile.profile_image else None
        form = ProfileImageForm(request.POST, request.FILES, instance=user_profile)
        if not form.is_valid():
            logger.warning(
                "%s.post() rejected a profile image from user %s: %s",
                self.formatted_class_name,
                request.user,
                form.errors.as_json(),
            )
            return http.JsonResponse(status=HTTPStatus.BAD_REQUEST.value, data=form.errors)
        form.save()
        if previous:
            user_profile.profile_image.storage.delete(previous)
        logger.info("%s.post() saved a profile image for user %s", self.formatted_class_name, request.user)
        return self._response(request, user_profile)

    def delete(self, request, *args, **kwargs):
        user_profile = self.own_user_profile(request)
        if user_profile.profile_image:
            user_profile.profile_image.delete(save=True)
            logger.info("%s.delete() removed the profile image of user %s", self.formatted_class_name, request.user)
        return self._response(request, user_profile)
