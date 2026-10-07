# pylint: disable=W0613
"""The Budget detail view of the Smarter web console: the Budget's manifest, with the spending of each resource."""

from typing import Optional

import yaml
from django.http import HttpResponse
from django.shortcuts import render

from smarter.apps.account.models import Budget
from smarter.apps.account.models.budget import is_visible
from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.views.base import DocsBaseView
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class BudgetDetailView(DocsBaseView):
    """
    Render a Budget's manifest, as ``smarter describe budget <name>`` returns it.

    Superusers see every Budget. Others see those attached to a resource that they may see.
    """

    template_path = "common/manifest_detail.html"
    budget: Optional[Budget] = None

    def get(self, request, *args, **kwargs) -> HttpResponse:
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

        pk_id = Budget.id_from_hashed_id(kwargs.pop("hashed_id"))
        self.budget = Budget.objects.filter(id=pk_id).first() if pk_id else None
        if self.budget is None or not self.user_profile:
            return SmarterHttpResponseNotFound(request=request, error_message="Budget not found")
        if not self.user_profile.user.is_superuser and not any(
            is_visible(self.user_profile, locator)
            for locator in self.budget.constraints.values_list("resource_locator", flat=True)  # type: ignore[attr-defined]
        ):
            return SmarterHttpResponseNotFound(request=request, error_message="Budget not found")

        self.kind = SAMKinds.BUDGET
        kwargs["name"] = self.budget.name
        kwargs["kind"] = self.kind.value
        json_response = self.get_brokered_json_response(
            ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe,
            ApiV1CliDescribeApiView.as_view(),
            request,
            *args,
            **kwargs,
        )
        context = {
            "manifest": yaml.dump(json_response, default_flow_style=False),
            "page_title": self.budget.name,
        }
        return render(request, self.template_path, context=context)
