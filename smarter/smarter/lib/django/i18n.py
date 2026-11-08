"""The languages that the web console offers."""

from django.conf import settings
from django.utils import translation


def console_languages() -> list[tuple[str, str]]:
    """
    The languages of ``settings.LANGUAGES``, each in its own name, as the console's language menu lists them.

    .. code-block:: python

        console_languages()
        # [("en", "English"), ("es", "Español"), ("fr", "Français"), ("pt-br", "Português Brasileiro")]

    :returns: ``(code, name)`` pairs, in the order of ``settings.LANGUAGES``. Each name starts with a
        capital letter.
    :rtype: list[tuple[str, str]]
    """
    languages = []
    for code, _ in settings.LANGUAGES:
        info = translation.get_language_info(code)
        local_name = info["name_local"]
        name = local_name[:1].upper() + local_name[1:]
        languages.append((info["code"], name))
    return languages
