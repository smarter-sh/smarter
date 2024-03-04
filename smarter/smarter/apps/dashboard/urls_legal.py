# -*- coding: utf-8 -*-
"""URL configuration for dashboard legal pages."""

from django.urls import path

from .views.legal import (
    AcceptableUseView,
    CookiePolicyView,
    LegalView,
    PCIComplianceView,
    PrivacyPolicyView,
    SLAView,
    TOSView,
)


urlpatterns = [
    path("", LegalView.as_view(), name="legal"),
    path("tos/", TOSView.as_view(), name="terms_of_service"),
    path("sla/", SLAView.as_view(), name="service_level_agreement"),
    path("acceptable-use/", AcceptableUseView.as_view(), name="acceptable_use"),
    path("privacy-policy/", PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("cookie-policy/", CookiePolicyView.as_view(), name="cookie_policy"),
    path("pci-compliance/", PCIComplianceView.as_view(), name="pci_compliance"),
]
