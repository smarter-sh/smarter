# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The branding settings of the organization that operates a Smarter platform."""

from typing import Optional

from pydantic import AnyUrl, BaseModel, EmailStr, Field, HttpUrl

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.util import before_field_validator
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django.validators import SmarterValidator


class BrandingSettings(BaseModel):
    """The platform operator's branding: name, address, contacts, links and logo."""

    branding_corporate_name: str = Field(
        settings_defaults.BRANDING_CORPORATE_NAME,
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
    :default: Value from ``settings_defaults.BRANDING_CORPORATE_NAME``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_corporate_name")
    def validate_branding_corporate_name(cls, v: Optional[str]) -> str:
        """Validates the `branding_corporate_name` field.

        Args:
            v (Optional[str]): The branding corporate name value to validate.

        Returns:
            str: The validated branding corporate name.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CORPORATE_NAME

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_corporate_name of type {type(v)} is not a str.")

        return v

    branding_support_phone_number: str = Field(
        settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER,
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
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_support_phone_number")
    def validate_branding_support_phone_number(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_phone_number` field.

        Args:
            v (Optional[str]): The branding support phone number value to validate.

        Returns:
            str: The validated branding support phone number.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_PHONE_NUMBER

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_phone_number of type {type(v)} is not a str.")

        return v

    branding_support_email: EmailStr = Field(
        settings_defaults.BRANDING_SUPPORT_EMAIL,
        description="The support email address used for branding purposes throughout the platform.",
        title="Branding Support Email",
    )
    """
    The support email address used for branding purposes throughout the platform.

    This setting specifies the email address that users can contact for support
    or assistance related to the platform. It is used in various branding contexts,
    such as email templates, user interfaces, and documentation.
    :type: EmailStr
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_EMAIL``
    :raises SmarterConfigurationError: If the value is not a EmailStr.
    """

    @before_field_validator("branding_support_email")
    def validate_branding_support_email(cls, v: Optional[EmailStr]) -> EmailStr:
        """Validates the `branding_support_email` field.

        Args:
            v (Optional[EmailStr]): The branding support email value to validate.
        Returns:
            EmailStr: The validated branding support email.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_EMAIL

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_email of type {type(v)} is not a EmailStr.")
        SmarterValidator.validate_email(v)

        return v

    branding_address1: str = Field(
        settings_defaults.BRANDING_ADDRESS1,
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
    :default: Value from ``settings_defaults.BRANDING_ADDRESS1``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_address1")
    def validate_branding_address(cls, v: Optional[str]) -> str:
        """Validates the `branding_address1` field.

        Args:
            v (Optional[str]): The branding address value to validate.

        Returns:
            str: The validated branding address.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_ADDRESS1

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_address1 of type {type(v)} is not a str.")

        return v

    branding_address2: Optional[str] = Field(
        settings_defaults.BRANDING_ADDRESS2,
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
    :default: Value from ``settings_defaults.BRANDING_ADDRESS2``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_address2")
    def validate_branding_address2(cls, v: Optional[str]) -> Optional[str]:
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

    branding_city: str = Field(
        settings_defaults.BRANDING_CITY,
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
    :default: Value from ``settings_defaults.BRANDING_CITY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_city")
    def validate_branding_city(cls, v: Optional[str]) -> str:
        """Validates the `branding_city` field.

        Args:
            v (Optional[str]): The branding city value to validate.

        Returns:
            str: The validated branding city.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CITY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_city of type {type(v)} is not a str.")

        return v

    branding_state: str = Field(
        settings_defaults.BRANDING_STATE,
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
    :default: Value from ``settings_defaults.BRANDING_STATE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_state")
    def validate_branding_state(cls, v: Optional[str]) -> str:
        """Validates the `branding_state` field.

        Args:
            v (Optional[str]): The branding state value to validate.

        Returns:
            str: The validated branding state.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_STATE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_state of type {type(v)} is not a str.")

        return v

    branding_postal_code: str = Field(
        settings_defaults.BRANDING_POSTAL_CODE,
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
    :default: Value from ``settings_defaults.BRANDING_POSTAL_CODE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_postal_code")
    def validate_branding_postal_code(cls, v: Optional[str]) -> str:
        """Validates the `branding_postal_code` field.

        Args:
            v (Optional[str]): The branding postal code value to validate.

        Returns:
            str: The validated branding postal code.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_POSTAL_CODE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_postal_code of type {type(v)} is not a str.")

        return v

    branding_country: str = Field(
        settings_defaults.BRANDING_COUNTRY,
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
    :default: Value from ``settings_defaults.BRANDING_COUNTRY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_country")
    def validate_branding_country(cls, v: Optional[str]) -> str:
        """Validates the `branding_country` field.

        Args:
            v (Optional[str]): The branding country value to validate.

        Returns:
            str: The validated branding country.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_COUNTRY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_country of type {type(v)} is not a str.")

        return v

    branding_currency: str = Field(
        settings_defaults.BRANDING_CURRENCY,
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
    :default: Value from ``settings_defaults.BRANDING_CURRENCY``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_currency")
    def validate_branding_currency(cls, v: Optional[str]) -> str:
        """Validates the `branding_currency` field.

        Args:
            v (Optional[str]): The branding currency value to validate.

        Returns:
            str: The validated branding currency.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_CURRENCY

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_currency of type {type(v)} is not a str.")

        return v

    branding_timezone: str = Field(
        settings_defaults.BRANDING_TIMEZONE,
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
    :default: Value from ``settings_defaults.BRANDING_TIMEZONE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_timezone")
    def validate_branding_timezone(cls, v: Optional[str]) -> str:
        """Validates the `branding_timezone` field.

        Args:
            v (Optional[str]): The branding timezone value to validate.

        Returns:
            str: The validated branding timezone.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_TIMEZONE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_timezone of type {type(v)} is not a str.")

        return v

    branding_contact_url: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_CONTACT_URL,
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
    :default: Value from ``settings_defaults.BRANDING_CONTACT_URL``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_contact_url")
    def validate_branding_contact_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_contact_url` field.

        Args:
            v (Optional[HttpUrl]): The branding contact URL value to validate.

        Returns:
            Optional[HttpUrl]: The validated branding contact URL.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_CONTACT_URL
        return v

    branding_primary_contact: str = Field(
        settings_defaults.BRANDING_PRIMARY_CONTACT,
        description="The name of the person who is the technical point of contact for this platform.",
        examples=["Lawrence McDaniel"],
        title="Branding Primary Contact",
    )
    """
    The name of the person who is the technical point of contact for this platform.

    This setting names the person who hosts the platform and answers its users' questions.
    The welcome email is written from this person, and signed with this name.
    :type: str
    :default: Value from ``settings_defaults.BRANDING_PRIMARY_CONTACT``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_primary_contact")
    def validate_branding_primary_contact(cls, v: Optional[str]) -> str:
        """Validates the `branding_primary_contact` field.

        Args:
            v (Optional[str]): The branding primary contact value to validate.

        Returns:
            str: The validated branding primary contact.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_PRIMARY_CONTACT

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_primary_contact of type {type(v)} is not a str.")

        return v

    branding_support_hours: str = Field(
        settings_defaults.BRANDING_SUPPORT_HOURS,
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
    :default: Value from ``settings_defaults.BRANDING_SUPPORT_HOURS``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("branding_support_hours")
    def validate_branding_support_hours(cls, v: Optional[str]) -> str:
        """Validates the `branding_support_hours` field.

        Args:
            v (Optional[str]): The branding support hours value to validate.

        Returns:
            str: The validated branding support hours.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.BRANDING_SUPPORT_HOURS

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"branding_support_hours of type {type(v)} is not a str.")

        return v

    branding_url_facebook: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_FACEBOOK,
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
    :default: Value from ``settings_defaults.BRANDING_URL_FACEBOOK``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_facebook")
    def validate_branding_url_facebook(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_facebook` field.

        Args:
            v (Optional[HttpUrl]): The branding URL Facebook value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Facebook.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_FACEBOOK
        return v

    branding_url_twitter: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_TWITTER,
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
    :default: Value from ``settings_defaults.BRANDING_URL_TWITTER``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_twitter")
    def validate_branding_url_twitter(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_twitter` field.

        Args:
            v (Optional[HttpUrl]): The branding URL Twitter value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL Twitter.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_TWITTER
        return v

    branding_url_linkedin: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_LINKEDIN,
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
    :default: Value from ``settings_defaults.BRANDING_URL_LINKEDIN``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_linkedin")
    def validate_branding_url_linkedin(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_linkedin` field.

        Args:
            v (Optional[HttpUrl]): The branding URL LinkedIn value to validate.
        Returns:
            Optional[HttpUrl]: The validated branding URL LinkedIn.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_LINKEDIN
        return v

    branding_url_slack: Optional[HttpUrl] = Field(
        settings_defaults.BRANDING_URL_SLACK,
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
    :default: Value from ``settings_defaults.BRANDING_URL_SLACK``
    :raises SmarterConfigurationError: If the value is not a valid HttpUrl.
    """

    @before_field_validator("branding_url_slack")
    def validate_branding_url_slack(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validates the `branding_url_slack` field.

        Args:
            v (Optional[HttpUrl]): The Slack invite link to validate.
        Returns:
            Optional[HttpUrl]: The validated Slack invite link.
        """
        if v is None or v == "":
            return settings_defaults.BRANDING_URL_SLACK
        return v

    logo: Optional[AnyUrl] = Field(
        settings_defaults.LOGO,
        description="The URL to the platform's logo image.",
        examples=["https://cdn.example.com/logo.png"],
        title="Platform Logo URL",
    )
    """
    The URL to the platform's logo image.

    This setting specifies the web address of the logo image used in the platform's user interface.
    It should be a valid URL pointing to an external image resource accessible by the frontend.

    :type: Optional[AnyUrl]
    :default: Value from ``settings_defaults.LOGO``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("logo")
    def validate_logo(cls, v: Optional[AnyUrl]) -> AnyUrl:
        """Validates the `logo` field.

        Args:
            v (Optional[AnyUrl]): The logo value to validate.

        Returns:
            AnyUrl: The validated logo.
        """
        if v is None:
            return settings_defaults.LOGO
        return v

    marketing_site_url: Optional[HttpUrl] = Field(
        settings_defaults.MARKETING_SITE_URL,
        description="The URL to the platform's marketing site.",
        examples=["https://www.example.com"],
        title="Marketing Site URL",
    )
    """
    The URL to the platform's marketing site.

    This setting specifies the web address of the marketing site associated
    with the platform. It should be a valid URL pointing to an external website.

    :type: Optional[httpHttpUrl]
    :default: Value from ``settings_defaults.MARKETING_SITE_URL``
    :raises SmarterConfigurationError: If the value is not a valid URL string.
    """

    @before_field_validator("marketing_site_url")
    def validate_marketing_site_url(cls, v: Optional[HttpUrl]) -> HttpUrl:
        """Validates the `marketing_site_url` field.

        Args:
            v (Optional[HttpUrl]): The marketing site URL value to validate.
        Returns:
            HttpUrl: The validated marketing site URL.
        """
        if str(v) in THE_EMPTY_SET and settings_defaults.MARKETING_SITE_URL is not None:
            return settings_defaults.MARKETING_SITE_URL
        return v  # type: ignore


__all__ = ["BrandingSettings"]
