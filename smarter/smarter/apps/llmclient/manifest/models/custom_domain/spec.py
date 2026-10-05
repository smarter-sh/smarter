"""
Smarter API Manifest - CustomDomain.spec.

A CustomDomain is a domain name that serves LLMClients from the customer's own
brand, rather than from the platform's default domain. ``smarter deploy``
registers it: Smarter creates an AWS Route53 hosted zone and a TLS certificate
for it, and the domain is verified once its NS records are added to the root
domain's DNS settings. An LLMClient uses it with its ``spec.customDomain``.

.. code-block:: yaml

    spec:
      config:
        domainName: llmclients.example.com
"""

import os
from typing import ClassVar

from pydantic import Field, field_validator

from smarter.apps.llmclient.manifest.models.custom_domain.const import MANIFEST_KIND
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMCustomDomainSpecConfig(AbstractSAMSpecBase):
    """Smarter API CustomDomain Manifest - CustomDomain.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".config"

    domainName: str = Field(
        ...,
        description=(
            f"{class_identifier}.domainName[str]. Required. The domain name, e.g. 'llmclients.example.com'. "
            "It cannot be changed once the domain has been registered."
        ),
    )

    @field_validator("domainName")
    @classmethod
    def validate_domain_name(cls, v: str) -> str:
        v = v.strip().lower().rstrip(".")
        try:
            SmarterValidator.validate_domain(v)
        except Exception as e:
            raise SAMValidationError(f"{cls.class_identifier}.domainName '{v}' is not a valid domain name.") from e
        return v


class SAMCustomDomainSpec(AbstractSAMSpecBase):
    """Smarter API CustomDomain Manifest - CustomDomain.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMCustomDomainSpecConfig = Field(
        ...,
        description=f"{class_identifier}.config[object]. Required. The configuration of the {MANIFEST_KIND}.",
    )
