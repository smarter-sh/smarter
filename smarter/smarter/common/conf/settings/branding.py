# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The branding settings of the organization that operates a Smarter platform."""

from typing import Optional
from urllib.parse import urljoin

from pydantic import AnyUrl, BaseModel, EmailStr, Field, HttpUrl, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.util import (
    before_field_validator,
    field_default,
    input_value,
    with_derived_default,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django.validators import SmarterValidator


class BrandingSettings(BaseModel):
    """The platform operator's branding: name, address, contacts, links and logo."""

    platform_branding_app_name: str = Field(
        "Smarter",
        description="The application's name, which prefixes the names of the platform's Django apps in the admin and the web console.",
        examples=["Acme AI"],
        title="Branding App Name",
    )
    """
    The application's name, which prefixes the names of the platform's Django apps in the admin and the web console: ``SMARTER_PLATFORM_BRANDING_APP_NAME``.

    :type: str
    :default: ``"Smarter"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_app_name")
    def validate_platform_branding_app_name(cls, v: Optional[str]) -> str:
        """
        Validate ``platform_branding_app_name``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_app_name")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"platform_branding_app_name of type {type(v)} is not a str.")
        return v

    platform_branding_product_name: str = Field(
        "The Smarter Project",
        description="The product's name, shown in the web console, emails and documentation.",
        examples=["Acme AI Platform"],
        title="Branding Product Name",
    )
    """
    The product's name, shown in the web console, emails and documentation: ``SMARTER_PLATFORM_BRANDING_PRODUCT_NAME``.

    :type: str
    :default: ``"The Smarter Project"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_product_name")
    def validate_platform_branding_product_name(cls, v: Optional[str]) -> str:
        """
        Validate ``platform_branding_product_name``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_product_name")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"platform_branding_product_name of type {type(v)} is not a str.")
        return v

    platform_branding_product_description: str = Field(
        "An open source, no-code AI authoring platform designed for instructional use.",
        description="A one-sentence description of the product, shown in the web console and in page metadata.",
        examples=["A no-code AI platform for Acme's teams."],
        title="Branding Product Description",
    )
    """
    A one-sentence description of the product, shown in the web console and in page metadata: ``SMARTER_PLATFORM_BRANDING_PRODUCT_DESCRIPTION``.

    :type: str
    :default: ``"An open source, no-code AI authoring platform designed for instructional use."``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_product_description")
    def validate_platform_branding_product_description(cls, v: Optional[str]) -> str:
        """
        Validate ``platform_branding_product_description``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_product_description")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"platform_branding_product_description of type {type(v)} is not a str.")
        return v

    platform_branding_cdn_url: HttpUrl = Field(
        HttpUrl("https://cdn.smarter.sh"),
        description="The CDN of the product's own static assets, e.g. its logo and Open Graph image.",
        examples=["https://cdn.example.com"],
        title="Branding CDN URL",
    )
    """
    The CDN of the product's own static assets, e.g. its logo and Open Graph image: ``SMARTER_PLATFORM_BRANDING_CDN_URL``.

    :type: HttpUrl
    :default: ``"https://cdn.smarter.sh"``
    """

    @before_field_validator("platform_branding_cdn_url")
    def validate_platform_branding_cdn_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """
        Validate ``platform_branding_cdn_url``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        """
        if v is None or v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_cdn_url")
        return v

    platform_branding_docs_url: HttpUrl = Field(
        HttpUrl("https://docs.smarter.sh"),
        description="The product's documentation site, linked from the web console and the api.",
        examples=["https://docs.example.com"],
        title="Branding Documentation URL",
    )
    """
    The product's documentation site, linked from the web console and the api: ``SMARTER_PLATFORM_BRANDING_DOCS_URL``.

    :type: HttpUrl
    :default: ``"https://docs.smarter.sh"``
    """

    @before_field_validator("platform_branding_docs_url")
    def validate_platform_branding_docs_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """
        Validate ``platform_branding_docs_url``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        """
        if v is None or v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_docs_url")
        return v

    platform_branding_blog_url: HttpUrl = Field(
        HttpUrl("https://blog.smarter.sh"),
        description="The product's blog, e.g. its release announcements.",
        examples=["https://blog.example.com"],
        title="Branding Blog URL",
    )
    """
    The product's blog, e.g. its release announcements: ``SMARTER_PLATFORM_BRANDING_BLOG_URL``.

    :type: HttpUrl
    :default: ``"https://blog.smarter.sh"``
    """

    @before_field_validator("platform_branding_blog_url")
    def validate_platform_branding_blog_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """
        Validate ``platform_branding_blog_url``: an empty value is the default.

        :param v: The value.
        :returns: The value, or the default.
        """
        if v is None or v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_blog_url")
        return v

    platform_branding_corporate_name: str = Field(
        "Lawrence P. McDaniel",
        description="The corporate name used for branding purposes throughout the platform.",
        examples=["Acme Corporation"],
        title="Branding Corporate Name",
    )
    """
    The corporate name used for branding purposes throughout the platform.

    This setting specifies the name of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"Lawrence P. McDaniel"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_corporate_name")
    def validate_platform_branding_corporate_name(cls, v: Optional[str]) -> str:
        """Validates the `branding_corporate_name` field.

        Args:
            v (Optional[str]): The branding corporate name value to validate.

        Returns:
            str: The validated branding corporate name.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_corporate_name")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_corporate_name of type {type(v)} is not a str.")

        return v

    platform_branding_support_phone_number: str = Field(
        "(###) 555-1212",
        description="The support phone number used for branding purposes throughout the platform.",
        examples=["+1-800-555-1234"],
        title="Branding Support Phone Number",
    )
    """
    The support phone number used for branding purposes throughout the platform.

    This setting specifies the phone number that users can call for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"(###) 555-1212"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_support_phone_number")
    def validate_platform_branding_support_phone_number(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_phone_number` field.

        Args:
            v (Optional[str]): The branding support phone number value to validate.

        Returns:
            str: The validated branding support phone number.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_support_phone_number")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_phone_number of type {type(v)} is not a str.")

        return v

    platform_branding_support_email: EmailStr = Field(
        "lpm0073@gmail.com",
        description="The support email address used for branding purposes throughout the platform.",
        title="Branding Support Email",
    )
    """
    The support email address used for branding purposes throughout the platform.

    This setting specifies the email address that users can contact for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: EmailStr
    :default: ``"lpm0073@gmail.com"``
    :raises SmarterConfigurationError: If the value is not a EmailStr.
    """

    @before_field_validator("platform_branding_support_email")
    def validate_platform_branding_support_email(cls, v: Optional[EmailStr]) -> EmailStr:
        """Validates the `branding_support_email` field.

        Args:
            v (Optional[EmailStr]): The branding support email value to validate.
        Returns:
            EmailStr: The validated branding support email.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_support_email")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_email of type {type(v)} is not a EmailStr.")
        SmarterValidator.validate_email(v)

        return v

    platform_branding_address1: str = Field(
        "123 Main St, Anytown, USA",
        description="The corporate address used for branding purposes throughout the platform.",
        examples=["123 Main St, Anytown, USA"],
        title="Branding Address",
    )
    """
    The corporate address used for branding purposes throughout the platform.

    This setting specifies the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"123 Main St, Anytown, USA"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_address1")
    def validate_branding_address(cls, v: Optional[str]) -> str:
        """Validates the `branding_address1` field.

        Args:
            v (Optional[str]): The branding address value to validate.

        Returns:
            str: The validated branding address.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_address1")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address1 of type {type(v)} is not a str.")

        return v

    platform_branding_address2: Optional[str] = Field(
        "Suite 100",
        description="The second line of the corporate address used for branding purposes throughout the platform.",
        examples=["Suite 100"],
        title="Branding Address Line 2",
    )
    """
    The second line of the corporate address used for branding purposes throughout the platform.

    This setting specifies the second line of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[str]
    :default: ``"Suite 100"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_address2")
    def validate_platform_branding_address2(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `branding_address2` field.

        Args:
            v (Optional[str]): The branding address line 2 value to validate.

        Returns:
            Optional[str]: The validated branding address line 2.
        """
        if v in THE_EMPTY_SET:
            return None

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address2 of type {type(v)} is not a str.")

        return v

    platform_branding_city: str = Field(
        "Anytown",
        description="The corporate city used for branding purposes throughout the platform.",
        examples=["Anytown"],
        title="Branding City",
    )
    """
    The corporate city used for branding purposes throughout the platform.

    This setting specifies the city of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"Anytown"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_city")
    def validate_platform_branding_city(cls, v: Optional[str]) -> str:
        """Validates the `branding_city` field.

        Args:
            v (Optional[str]): The branding city value to validate.

        Returns:
            str: The validated branding city.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_city")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_city of type {type(v)} is not a str.")

        return v

    platform_branding_state: str = Field(
        "CA",
        description="The corporate state used for branding purposes throughout the platform.",
        examples=["CA"],
        title="Branding State",
    )
    """
    The corporate state used for branding purposes throughout the platform.

    This setting specifies the state of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"CA"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_state")
    def validate_platform_branding_state(cls, v: Optional[str]) -> str:
        """Validates the `branding_state` field.

        Args:
            v (Optional[str]): The branding state value to validate.

        Returns:
            str: The validated branding state.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_state")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_state of type {type(v)} is not a str.")

        return v

    platform_branding_postal_code: str = Field(
        "12345",
        description="The corporate postal code used for branding purposes throughout the platform.",
        examples=["12345"],
        title="Branding Postal Code",
    )
    """
    The corporate postal code used for branding purposes throughout the platform.

    This setting specifies the postal code of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"12345"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_postal_code")
    def validate_platform_branding_postal_code(cls, v: Optional[str]) -> str:
        """Validates the `branding_postal_code` field.

        Args:
            v (Optional[str]): The branding postal code value to validate.

        Returns:
            str: The validated branding postal code.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_postal_code")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_postal_code of type {type(v)} is not a str.")

        return v

    platform_branding_country: str = Field(
        "USA",
        description="The corporate country used for branding purposes throughout the platform.",
        examples=["USA"],
        title="Branding Country",
    )
    """
    The corporate country used for branding purposes throughout the platform.

    This setting specifies the country of the physical address of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"USA"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_country")
    def validate_platform_branding_country(cls, v: Optional[str]) -> str:
        """Validates the `branding_country` field.

        Args:
            v (Optional[str]): The branding country value to validate.

        Returns:
            str: The validated branding country.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_country")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_country of type {type(v)} is not a str.")

        return v

    platform_branding_currency: str = Field(
        "USD",
        description="The currency used for branding purposes throughout the platform.",
        examples=["USD"],
        title="Branding Currency",
    )
    """
    The currency used for branding purposes throughout the platform.

    This setting specifies the currency that is used in various branding contexts,
    such as email templates, user interfaces, and documentation. It can be used to
    indicate the currency in which prices, billing, or financial information
    is presented to users.
    :type: str
    :default: ``"USD"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_currency")
    def validate_platform_branding_currency(cls, v: Optional[str]) -> str:
        """Validates the `branding_currency` field.

        Args:
            v (Optional[str]): The branding currency value to validate.

        Returns:
            str: The validated branding currency.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_currency")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_currency of type {type(v)} is not a str.")

        return v

    platform_branding_timezone: str = Field(
        "America/Denver",
        description="The timezone used for branding purposes throughout the platform.",
        examples=["America/New_York"],
        title="Branding Timezone",
    )
    """
    The timezone used for branding purposes throughout the platform.

    This setting specifies the timezone that is used in various branding contexts,
    such as email templates, user interfaces, and documentation. It can be used to
    indicate the timezone in which dates and times are presented to users.
    :type: str
    :default: ``"America/Denver"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_timezone")
    def validate_platform_branding_timezone(cls, v: Optional[str]) -> str:
        """Validates the `branding_timezone` field.

        Args:
            v (Optional[str]): The branding timezone value to validate.

        Returns:
            str: The validated branding timezone.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_timezone")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_timezone of type {type(v)} is not a str.")

        return v

    platform_branding_contact_url: Optional[HttpUrl] = Field(
        HttpUrl("https://lawrencemcdaniel.com/"),
        description="The contact URL used for branding purposes throughout the platform.",
        examples=["https://www.example.com/contact"],
        title="Branding Contact URL",
    )
    """
    The contact URL used for branding purposes throughout the platform.

    This setting specifies the URL that users can visit to contact
    the organization or company that owns or operates the platform.
    It is used in various branding contexts, such as email templates,
    user interfaces, and documentation.
    :type: str
    :default: ``"https://lawrencemcdaniel.com/"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_contact_url")
    def validate_platform_branding_contact_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_contact_url` field.

        Args:
            v (Optional[HttpUrl]): The branding contact URL value to validate.

        Returns:
            Optional[HttpUrl]: The validated branding contact URL.
        """
        if v is None or v == "":
            return field_default(cls, "platform_branding_contact_url")
        return v

    platform_branding_primary_contact: str = Field(
        "Lawrence McDaniel",
        description="The name of the person who is the technical point of contact for this platform.",
        examples=["Lawrence McDaniel"],
        title="Branding Primary Contact",
    )
    """
    The name of the person who is the technical point of contact for this platform.

    This setting names the person who hosts the platform and answers its users' questions.
    The welcome email is written from this person, and signed with this name.
    :type: str
    :default: ``"Lawrence McDaniel"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_primary_contact")
    def validate_platform_branding_primary_contact(cls, v: Optional[str]) -> str:
        """Validates the `branding_primary_contact` field.

        Args:
            v (Optional[str]): The branding primary contact value to validate.

        Returns:
            str: The validated branding primary contact.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_primary_contact")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_primary_contact of type {type(v)} is not a str.")

        return v

    platform_branding_support_hours: str = Field(
        "MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)",
        description="The support hours used for branding purposes throughout the platform.",
        examples=["Mon-Fri 9am-5pm EST"],
        title="Branding Support Hours",
    )
    """
    The support hours used for branding purposes throughout the platform.

    This setting specifies the hours during which support is available
    for users of the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: str
    :default: ``"MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_branding_support_hours")
    def validate_platform_branding_support_hours(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_hours` field.

        Args:
            v (Optional[str]): The branding support hours value to validate.

        Returns:
            str: The validated branding support hours.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_branding_support_hours")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_hours of type {type(v)} is not a str.")

        return v

    platform_branding_url_facebook: Optional[HttpUrl] = Field(
        HttpUrl("https://facebook.com"),
        description="The Facebook URL used for branding purposes throughout the platform.",
        examples=["https://www.facebook.com/example"],
        title="Branding URL Facebook",
    )
    """
    The Facebook URL used for branding purposes throughout the platform.

    This setting specifies the Facebook page URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: ``"https://facebook.com"``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("platform_branding_url_facebook")
    def validate_platform_branding_url_facebook(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_facebook` field.

        Args:
            v (Optional[HttpUrl]): The branding URL Facebook value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Facebook.
        """
        if v is None or v == "":
            return field_default(cls, "platform_branding_url_facebook")
        return v

    platform_branding_url_twitter: Optional[HttpUrl] = Field(
        HttpUrl("https://x.com/fullstackwlarry"),
        description="The Twitter URL used for branding purposes throughout the platform.",
        examples=["https://www.twitter.com/example"],
        title="Branding URL Twitter",
    )
    """
    The Twitter URL used for branding purposes throughout the platform.

    This setting specifies the Twitter profile URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: ``"https://x.com/fullstackwlarry"``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("platform_branding_url_twitter")
    def validate_platform_branding_url_twitter(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_twitter` field.

        Args:
            v (Optional[HttpUrl]): The branding URL Twitter value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Twitter.
        """
        if v is None or v == "":
            return field_default(cls, "platform_branding_url_twitter")
        return v

    platform_branding_url_linkedin: Optional[HttpUrl] = Field(
        HttpUrl("https://www.linkedin.com/in/lawrencemcdaniel/"),
        description="The LinkedIn URL used for branding purposes throughout the platform.",
        examples=["https://www.linkedin.com/company/example"],
        title="Branding URL LinkedIn",
    )
    """
    The LinkedIn URL used for branding purposes throughout the platform.

    This setting specifies the LinkedIn profile URL of the organization or company that owns
    or operates the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: Optional[HttpUrl]
    :default: ``"https://www.linkedin.com/in/lawrencemcdaniel/"``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("platform_branding_url_linkedin")
    def validate_platform_branding_url_linkedin(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_linkedin` field.

        Args:
            v (Optional[HttpUrl]): The branding URL LinkedIn value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL LinkedIn.
        """
        if v is None or v == "":
            return field_default(cls, "platform_branding_url_linkedin")
        return v

    platform_branding_url_slack: Optional[HttpUrl] = Field(
        HttpUrl("https://join.slack.com/t/thesmarterproject/shared_invite/zt-4f0t6v46q-e2c5Of4hS4fBr_XwfQARCw"),
        description="The invite link of the Slack workspace that the platform's emails invite users to.",
        examples=["https://join.slack.com/t/example/shared_invite/zt-example"],
        title="Branding URL Slack",
    )
    """
    The invite link of the Slack workspace that the platform's emails invite users to.

    The welcome email links to it, and the Slack invitation email, which a Celery Beat task sends
    two days after the welcome email, is about it. The default is the invite link of The Smarter
    Project's Slack workspace.

    :type: Optional[HttpUrl]
    :default: ``"https://join.slack.com/t/thesmarterproject/shared_invite/zt-4f0t6v46q-e2c5Of4hS4fBr_XwfQARCw"``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("platform_branding_url_slack")
    def validate_platform_branding_url_slack(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_slack` field.

        Args:
            v (Optional[HttpUrl]): The Slack invite link to validate.
        Returns:
            Optional[HttpUrl]: The validated Slack invite link.
        """
        if v is None or v == "":
            return field_default(cls, "platform_branding_url_slack")
        return v

    platform_branding_logo: Optional[AnyUrl] = Field(
        None,
        description="The URL to the platform's logo image.",
        examples=["https://cdn.example.com/logo.png"],
        title="Platform Logo URL",
    )
    """
    The URL to the platform's logo image.

    This setting specifies the web address of the logo image used in the platform's user interface.
    It should be a valid URL pointing to an external image resource accessible by the frontend.

    :type: Optional[AnyUrl]
    :default: ``/images/logo/smarter-crop.png`` on :attr:`platform_branding_cdn_url`. See :meth:`derive_branding_defaults`.
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("platform_branding_logo")
    def validate_platform_branding_logo(cls, v: Optional[AnyUrl]) -> AnyUrl:
        """Validates the `logo` field.

        Args:
            v (Optional[AnyUrl]): The logo value to validate.

        Returns:
            AnyUrl: The validated logo.
        """
        if v is None:
            raise SmarterConfigurationError("platform_branding_logo is not set.")
        return v

    platform_branding_marketing_site_url: Optional[HttpUrl] = Field(
        None,
        description="The URL to the platform's marketing site.",
        examples=["https://www.example.com"],
        title="Marketing Site URL",
    )
    """
    The URL to the platform's marketing site.

    This setting specifies the web address of the marketing site associated
    with the platform. It should be a valid URL pointing to an external website.

    :type: Optional[httpHttpUrl]
    :default: ``https://`` the root domain, e.g. ``https://example.com``. See :meth:`derive_branding_defaults`.
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("platform_branding_marketing_site_url")
    def validate_platform_branding_marketing_site_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """Validates the `marketing_site_url` field.

        Args:
            v (Optional[HttpUrl]): The marketing site URL value to validate.
        Returns:
            HttpUrl: The validated marketing site URL.
        """
        return v  # type: ignore

    @model_validator(mode="before")
    @classmethod
    def derive_branding_defaults(cls, data: object) -> object:
        """
        Derive the logo and the marketing site's url, unless they are set.

        The logo is ``/images/logo/smarter-crop.png`` on the CDN, and the marketing site is ``https://``
        the root domain, which :class:`~smarter.common.conf.settings.platform.PlatformSettings` holds.

        :param data: The values to validate: the constructor's and the environment's.
        :returns: The values, with the derived defaults added.
        """
        cdn_url = input_value(cls, data, "platform_branding_cdn_url")
        logo = urljoin(str(cdn_url), "/images/logo/smarter-crop.png")
        data = with_derived_default(data, "platform_branding_logo", logo)
        if "platform_root_domain" not in cls.model_fields:
            return data
        root_domain = input_value(cls, data, "platform_root_domain")
        marketing_site_url = f"https://{root_domain}"
        return with_derived_default(data, "platform_branding_marketing_site_url", marketing_site_url)


__all__ = ["BrandingSettings"]
