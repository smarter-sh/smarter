Dashboard Authentication - Profile Image
==========================================

The web console shows a profile image for the signed-in user in the navbar's
user menu. :attr:`smarter.apps.account.models.UserProfile.avatar_url` chooses
it, in this order:

1. the image that the user uploaded, ``UserProfile.profile_image``;
2. the image that the oauth provider supplied when the user last signed in,
   ``UserProfile.profile_image_url``: Google's and LinkedIn's ``picture``, or
   GitHub's ``avatar_url``;
3. a default silhouette, ``static/images/avatars/default-profile.svg``.

To upload an image, click the image in the user menu, or choose
**Change Profile Image**. PNG, JPEG, GIF and WebP files of up to 2 MB are
accepted; SVG is not, because it can carry script. **Remove Profile Image**
deletes the upload, and the console falls back to the oauth image, if any.
Uploads are stored in Django's default storage (the platform's S3 bucket when
AWS is configured) under a random file name.

.. automodule:: smarter.apps.account.views.dashboard.profile_image
    :members:
    :undoc-members:
    :show-inheritance:
