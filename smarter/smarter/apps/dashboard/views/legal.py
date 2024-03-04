# -*- coding: utf-8 -*-
"""Django views"""
import logging

from smarter.view_helpers import SmarterAuthenticatedWebView


logger = logging.getLogger(__name__)


class TOSView(SmarterAuthenticatedWebView):
    """Terms of service view"""

    template_path = "dashboard/legal/tos.html"


class SLAView(SmarterAuthenticatedWebView):
    """Service level agreement view"""

    template_path = "dashboard/legal/sla.html"


class AcceptableUseView(SmarterAuthenticatedWebView):
    """Acceptable Use view"""

    template_path = "dashboard/legal/acceptable-use.html"


class PrivacyPolicyView(SmarterAuthenticatedWebView):
    """Privacy policy view"""

    template_path = "dashboard/legal/privacy-policy.html"


class CookiePolicyView(SmarterAuthenticatedWebView):
    """Cookie policy view"""

    template_path = "dashboard/legal/cookie-policy.html"


class PCIComplianceView(SmarterAuthenticatedWebView):
    """PCI Compliance view"""

    template_path = "dashboard/legal/pci-compliance.html"
