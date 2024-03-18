# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.apps.common.view_helpers import SmarterWebView


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LegalView(SmarterWebView):
    """Top level legal view"""

    template_path = "dashboard/legal/index.html"


class TOSView(SmarterWebView):
    """Terms of service view"""

    template_path = "dashboard/legal/tos.html"


class SLAView(SmarterWebView):
    """Service level agreement view"""

    template_path = "dashboard/legal/sla.html"


class AcceptableUseView(SmarterWebView):
    """Acceptable Use view"""

    template_path = "dashboard/legal/acceptable-use.html"


class PrivacyPolicyView(SmarterWebView):
    """Privacy policy view"""

    template_path = "dashboard/legal/privacy-policy.html"


class CookiePolicyView(SmarterWebView):
    """Cookie policy view"""

    template_path = "dashboard/legal/cookie-policy.html"


class PCIComplianceView(SmarterWebView):
    """PCI Compliance view"""

    template_path = "dashboard/legal/pci-compliance.html"
