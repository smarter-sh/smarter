"""
Django template tag for the web console's onboarding hints, which the React package ``@smarter/onboarding`` shows.

``templates/react/onboarding.html`` uses it, and the console's base template,
``templates/dashboard/base.html``, includes it on every page, for signed-in users.
"""

from django import template
from django.conf import settings
from django.template.context import RequestContext

from smarter.apps.account.models import get_resolved_user
from smarter.apps.dashboard.views.views.api.onboarding import onboarding_context
from smarter.lib.django.shortcuts import reverse
from smarter.lib.typing import SmarterDictType

register = template.Library()


@register.simple_tag(takes_context=True)
def onboarding(context: RequestContext) -> SmarterDictType:
    """
    The onboarding state of the page, which the page's React apps read as JSON.

    The api's url is reversed against ``settings.ROOT_URLCONF``, because the console's base template
    also renders on a deployed LLMClient's host, whose urlconf has none of the console's names.

    :param context: The template context, whose request's user is the signed-in user.
    :type context: django.template.context.RequestContext
    :returns: An :class:`~smarter.apps.dashboard.views.views.api.onboarding.OnboardingContext`, dumped
        with its camelCase aliases, for the ``json_script`` filter.
    :rtype: SmarterDictType
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
    from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

    namespaces = (DashboardReverseNames.namespace, DashboardApiReverseNames.namespace)
    api_url = reverse(*namespaces, DashboardApiReverseNames.onboarding_seen, urlconf=settings.ROOT_URLCONF)
    user = get_resolved_user(context["request"].user)
    return onboarding_context(user, api_url).model_dump(mode="json", by_alias=True)
