"""AWS helper base class."""

# python stuff
import logging
import os
from functools import cached_property
from typing import Optional
from urllib.parse import urlparse

import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
import botocore.exceptions

from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import Services, smarter_settings

# our stuff
from smarter.common.const import (
    SMARTER_API_SUBDOMAIN,
    SMARTER_PLATFORM_SUBDOMAIN,
    SmarterEnvironments,
)
from smarter.common.exceptions import SmarterException
from smarter.common.helpers.console_helpers import (
    formatted_text,
    formatted_text_green,
    formatted_text_red,
)

# mcdaniel apr-2024: technically we shouldn't import smarter.libe.django into the aws helpers
# but the validators don't depend on django initialization, so we're okay here.
from smarter.lib.django.validators import SmarterValidator, SmarterValueError


# from .exceptions import AWSNotReadyError


logger = logging.getLogger(__name__)


class SmarterAWSException(SmarterException):
    """Raised when the hosted zone is not found."""


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class AWSBase(SmarterHelperMixin):
    """
    Provides a foundational interface for interacting with AWS services in a secure, consistent, and environment-aware manner.

    This base class is responsible for initializing and managing AWS connections, ensuring that credentials and sessions
    are established only when the application is in a ready state. It supports multiple authentication strategies,
    including IAM role-based security (for environments like AWS Lambda), AWS profiles, and direct access key credentials.
    The class automatically detects the execution environment and adapts its behavior accordingly, such as recognizing
    when it is running inside AWS infrastructure.

    AWSBase also implements logic to determine whether the current environment is a recognized and authorized Smarter
    environment, which is critical for safely creating or modifying billable AWS resources. It provides mechanisms for
    reformatting and validating domain names, particularly transforming localhost or development domains into proxy domains
    compatible with AWS Route53 and Kubernetes, thereby supporting seamless local development and cloud deployment.

    The class exposes properties and methods for accessing AWS account identity, region, authentication sources, and
    session objects, as well as utility functions for domain validation and environment-specific configuration. It includes
    robust logging and error handling to facilitate debugging and operational transparency. By centralizing AWS connection
    logic and environment checks, AWSBase enables derived helper classes to focus on service-specific functionality while
    maintaining consistent security and configuration practices across the codebase.
    """

    LOCAL_HOSTS = smarter_settings.local_hosts

    _aws_access_key_id: Optional[str] = None
    _aws_secret_access_key: Optional[str] = None
    _aws_region: Optional[str] = None
    _aws_profile: Optional[str] = None

    _aws_access_key_id_source: Optional[str] = None
    _aws_secret_access_key_source: Optional[str] = None

    _authentication_credentials_are_initialized: bool = False
    _domain = None
    _aws_session = None
    _client = None
    _client_type: Optional[str] = None

    _root_domain: str = smarter_settings.root_domain
    _environment: str = smarter_settings.environment
    _environment_domain: Optional[str] = None
    _shared_resource_identifier: Optional[str] = None
    _debug_mode: bool = False

    _connected: bool = False
    _identity: Optional[dict] = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        shared_resource_identifier: Optional[str] = None,
        environment: Optional[str] = None,
        environment_domain: Optional[str] = None,
        root_domain: Optional[str] = None,
        debug_mode: bool = False,
        init_info: Optional[str] = None,
    ):
        Services.raise_error_on_disabled(Services.AWS_CLI)
        logger.debug("%s.__init__() initializing", self.formatted_class_name)

        self._shared_resource_identifier = shared_resource_identifier or smarter_settings.shared_resource_identifier
        self._environment = environment or smarter_settings.environment

        self._root_domain = root_domain or smarter_settings.root_domain
        self._environment_domain = environment_domain or smarter_settings.environment_platform_domain
        self._debug_mode = debug_mode or smarter_settings.debug_mode

        if init_info:
            logger.debug(init_info)

        # ----------------------------------------------------------------------
        # AWS authentication. Hereon we only want to initialize whatever is
        # needed to establish a connection to AWS.
        # ----------------------------------------------------------------------

        # priority 1: AWS IAM role based security
        if not self.authentication_credentials_are_initialized and self.is_aws_deployed:
            # If we're running inside AWS Lambda, then we don't need to set the AWS credentials.
            logger.debug("running inside AWS Lambda")
            self._aws_access_key_id_source = "overridden by IAM role-based security"
            self._aws_secret_access_key_source = "overridden by IAM role-based security"
            self._authentication_credentials_are_initialized = True

        # initialize creentials from smarter_settings unless any of these were passed as parameters
        self._aws_access_key_id = (
            aws_access_key_id or smarter_settings.aws_access_key_id.get_secret_value()
            if smarter_settings.aws_access_key_id
            else None
        )
        self._aws_secret_access_key = (
            aws_secret_access_key or smarter_settings.aws_secret_access_key.get_secret_value()
            if smarter_settings.aws_secret_access_key
            else None
        )
        self._aws_region = aws_region or smarter_settings.aws_region
        self._aws_profile = aws_profile or smarter_settings.aws_profile

        # priority 2: aws_profile
        if not self.authentication_credentials_are_initialized:
            if self.aws_profile:
                self._aws_access_key_id_source = "aws_profile"
                self._aws_secret_access_key_source = "aws_profile"
                self._authentication_credentials_are_initialized = True

        # priority 3: aws_access_key_id and aws_secret_access_key
        if (
            not self.authentication_credentials_are_initialized
            and self.aws_access_key_id
            and self.aws_secret_access_key
            and self.aws_region
        ):
            self._authentication_credentials_are_initialized = True
            self._aws_access_key_id_source = "passed parameter"
            self._aws_secret_access_key_source = "passed parameter"

        msg = f"{self.formatted_class_name}.__init__() is {self.authentication_credentials_state}"
        if self.authentication_credentials_are_initialized:
            logger.info(msg)
        else:
            logger.error(msg)

    @property
    def formatted_class_name(self) -> str:
        """
        Return formatted class name.

        :return: formatted class name
        :rtype: str
        """
        return formatted_text(f"{__name__}.{AWSBase.__name__}")

    @property
    def client(self):
        """
        Return the AWS client

        :return: boto3 client instance
        :rtype: a child of boto3.client
        """
        if self._client:
            return self._client

        if not self.client_type:
            raise SmarterAWSException("Client type is not specified.")

        if not self.ready:
            logger.error("%s.client() AWS session is not ready", self.formatted_class_name)
            return None
        try:
            logger.debug("%s.client() creating AWS %s client", self.formatted_class_name, self.client_type.upper())
            self._client = self.aws_session.client(self.client_type)
            msg = f"{self.formatted_class_name}.client() {formatted_text_green(f'AWS Boto {type(self._client).__name__} client created')}."
            logger.info(msg)
        except botocore.exceptions.BotoCoreError as e:
            logger.error(
                "%s.client() Failed to create AWS %s client: %s",
                self.formatted_class_name,
                self.client_type.upper(),
                str(e),
            )
            return None
        return self._client

    @property
    def client_type(self) -> Optional[str]:
        """
        Return the AWS client type.

        :return: AWS client type
        :rtype: Optional[str]
        """
        return self._client_type

    @property
    def identity(self) -> Optional[dict]:
        """
        Return the AWS identity for the current session.

        This property retrieves the identity information associated with the current AWS credentials,
        including the user ID, AWS account number, and IAM ARN. The identity is fetched using the AWS
        Security Token Service (STS) and is cached for subsequent calls.

        :return: A dictionary containing AWS identity details, or None if not available.
        :rtype: Optional[dict]

        Example output:

        .. code-block:: json

            {
                "UserId": "AIDARKEXDU3E7KD3L3CRF",
                "Account": "090511222473",
                "Arn": "arn:aws:iam::090511222473:user/mcdaniel",
                "ResponseMetadata": {
                    "RequestId": "4d20b844-7e75-4980-9e92-ca0867b24387",
                    "HTTPStatusCode": 200,
                    "HTTPHeaders": {
                        "x-amzn-requestid": "4d20b844-7e75-4980-9e92-ca0867b24387",
                        "x-amz-sts-extended-request-id": "MTp1cy1lYXN0LTI6UzoxNzYzNTc5NjUyMzA0OlI6MVFkeG8yZ1Q=",
                        "content-type": "text/xml",
                        "content-length": "405",
                        "date": "Wed, 19 Nov 2025 19:14:12 GMT"
                    },
                    "RetryAttempts": 0
                }
            }
        """
        if self._identity:
            return self._identity
        if not self.authentication_credentials_are_initialized:
            logger.warning("%s.identity requested but AWSBase is not initialized", self.formatted_class_name)
            return None

        try:
            logger.debug("%s.identity fetching AWS IAM identity", self.formatted_class_name)
            self._identity = self.aws_session.client("sts").get_caller_identity() if self.aws_session else None
        # pylint: disable=broad-exception-caught
        except Exception as e:
            msg = f"{self.formatted_class_name}.identity {formatted_text_red('could not fetch AWS IAM identity due to an error')}: {e}"
            logger.error(msg)
            self._identity = None

        if self._identity:
            msg = f"{self.formatted_class_name}.identity {formatted_text_green('successfully fetched AWS IAM identity.')}: {self._identity}"
            logger.info(msg)
        else:
            msg = f"{self.formatted_class_name}.identity {formatted_text_red('could not fetch AWS IAM identity.')}"
            logger.error(msg)
        return self._identity

    @cached_property
    def version(self):
        """
        Return the version.

        :return: boto3 version
        :rtype: str
        """
        return boto3.__version__

    @property
    def debug_mode(self):
        """
        Debug mode

        :return: debug mode
        :rtype: bool
        """
        return self._debug_mode

    @property
    def authentication_credentials_are_initialized(self):
        """
        Are aws authentication settings initialized?
        True if we have enoug information to try to connect to AWS.
        False otherwise.

        :return: True if initialized
        :rtype: bool
        """
        return self._authentication_credentials_are_initialized

    @property
    def is_aws_deployed(self) -> bool:
        """
        Return True if we're running inside of AWS Lambda.

        :return: True if running inside AWS Lambda
        :rtype: bool
        """
        return bool(os.environ.get("AWS_DEPLOYED", False))

    @property
    def aws_is_configured(self) -> bool:
        """
        Return True if AWS is configured.

        :return: True if AWS is configured
        :rtype: bool
        """
        return smarter_settings.aws_is_configured

    @property
    def aws_profile(self):
        """
        AWS profile

        :return: AWS profile
        :rtype: Optional[str]
        """
        return self._aws_profile

    @property
    def aws_account_id(self):
        """
        AWS account id

        :return: AWS account id
        :rtype: Optional[str]
        """
        if not self.ready:
            return None

        if not isinstance(self.identity, dict):
            return None

        return self.identity.get("Account", None)

    @property
    def aws_iam_arn(self):
        """
        AWS IAM ARN

        :return: AWS IAM ARN (Amazon Resource Name)
        :rtype: Optional[str]
        """
        if not self.ready:
            return None

        if not isinstance(self.identity, dict):
            return None

        return self.identity.get("Arn", None)

    @property
    def aws_region(self):
        """
        AWS region

        :return: AWS region (e.g. 'us-west-2')
        :rtype: Optional[str]
        """
        return self._aws_region

    @property
    def aws_access_key_id_source(self):
        """
        AWS access key id source

        :return: AWS access key id source
        :rtype: Optional[str]
        """
        return self._aws_access_key_id_source

    @property
    def aws_access_key_id(self):
        """
        AWS access key id

        :return: AWS access key id
        :rtype: Optional[str]
        """
        return self._aws_access_key_id

    @property
    def aws_secret_access_key_source(self):
        """
        AWS secret access key source
        :return: AWS secret access key source
        :rtype: Optional[str]
        """
        return self._aws_secret_access_key_source

    @property
    def aws_secret_access_key(self):
        """
        AWS secret access key

        :return: AWS secret access key
        :rtype: Optional[str]
        """
        return self._aws_secret_access_key

    @property
    def aws_auth(self) -> dict:
        """
        AWS authentication

        :return: AWS authentication details
        :rtype: dict
        """
        retval = {
            "aws_profile": self.aws_profile,
            "aws_access_key_id_source": self.aws_access_key_id_source,
            "aws_secret_access_key_source": self.aws_secret_access_key_source,
            "aws_region": self.aws_region,
        }
        return retval

    @property
    def aws_session(self):
        """
        AWS session

        :return: boto3 AWS session
        :rtype: Optional[boto3.Session]
        """
        if self._aws_session:
            return self._aws_session

        logger.debug("%s.aws_session() establishing AWS boto session", self.formatted_class_name)
        if not self.authentication_credentials_are_initialized:
            msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('AWSBase is not initialized')}"
            logger.error(msg)
            return None

        if self.aws_profile:
            try:
                self._aws_session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
            except botocore.exceptions.ProfileNotFound:
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red(f'Unable to establish AWS boto session: aws_profile {self.aws_profile} not found')}"
                logger.error(msg)

            if self._aws_session:
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_green('established AWS boto session using aws_profile')}: {self.aws_profile}"
                logger.info(msg)
                return self._aws_session
            else:
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('Unable to establish AWS boto session using aws_profile')}: {self.aws_profile}"
                logger.error(msg)

        if self.aws_access_key_id is not None and self.aws_secret_access_key is not None:
            try:
                self._aws_session = boto3.Session(
                    region_name=self.aws_region,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('Encountered an error while attempting to establish AWS boto session using aws key-pair')}: {e}"
                logger.error(msg)

            if self._aws_session:
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_green('established AWS boto session using aws key-pair')}"
                logger.info(msg)
                return self._aws_session
            else:
                msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('Unable to establish AWS boto session using aws key-pair')}"
                logger.error(msg)

        logger.warning("%s.aws_session() creating new aws_session without aws credentials", self.formatted_class_name)

        try:
            self._aws_session = boto3.Session(region_name=self.aws_region)
        except Exception as e:  # pylint: disable=broad-exception-caught
            msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('Encountered an error while attempting to establish AWS boto session without aws credentials')}: {e}"
            logger.error(msg)

        if self._aws_session:
            msg = f"{self.formatted_class_name}.aws_session() {formatted_text_green('established AWS boto session.')}"
            logger.info(msg)
        else:
            msg = f"{self.formatted_class_name}.aws_session() {formatted_text_red('Unable to establish AWS boto session.')}"
            logger.error(msg)

        return self._aws_session

    @property
    def shared_resource_identifier(self):
        """
        Return the shared resource identifier.

        :return: shared resource identifier
        :rtype: Optional[str]
        """
        return self._shared_resource_identifier

    @property
    def environment(self) -> str:
        """
        Return the environment.

        :return: environment
        :rtype: str
        """
        return self._environment

    @property
    def environment_domain(self) -> str:
        """
        we need to rebuild these in order to reformat the localhost domain into
        a proxy domain that will work with AWS Route53 and Kubernetes

        :return: environment domain
        :rtype: str
        """
        return f"{self.environment}.{SMARTER_PLATFORM_SUBDOMAIN}.{self.root_domain}"

    @property
    def environment_api_domain(self) -> str:
        """
        we need to rebuild these in order to reformat the localhost domain into
        a proxy domain that will work with AWS Route53 and Kubernetes

        :return: environment API domain
        :rtype: str
        """
        return f"{self.environment}.{SMARTER_API_SUBDOMAIN}.{self.root_domain}"

    @property
    def root_domain(self) -> str:
        """
        Return the root domain.

        :return: root domain
        :rtype: str
        """
        return self._root_domain

    # --------------------------------------------------------------------------
    # helper functions
    # --------------------------------------------------------------------------
    def domain_resolver(self, domain: str) -> str:
        """
        Validate the domain and swap out localhost for the proxy domain.

        :param domain: domain to validate
        :type domain: str
        """
        if self.environment == SmarterEnvironments.LOCAL:
            proxy_domain: Optional[str] = None
            if smarter_settings.environment_platform_domain in domain:
                proxy_domain = domain.replace(smarter_settings.environment_platform_domain, self.environment_domain)
            if smarter_settings.environment_api_domain in domain:
                proxy_domain = domain.replace(smarter_settings.environment_api_domain, self.environment_api_domain)
            if proxy_domain:
                SmarterValidator.validate_domain(domain)
                logger.info("replacing %s with proxy domain %s", domain, proxy_domain)
                return proxy_domain

        # catch-all to ensure that we don't find ourselves working
        # with anything boneheaded.
        parsed_domain = urlparse(f"http://{domain}")
        root_domain = parsed_domain.netloc
        if root_domain in self.LOCAL_HOSTS:
            raise SmarterValueError(f"Domain {root_domain} is prohibited.")

        # if we're not in a local environment, we don't need to do anything
        SmarterValidator.validate_domain(domain)
        return domain

    # --------------------------------------------------------------------------
    # AWS state functions
    # --------------------------------------------------------------------------
    @property
    def ready(self) -> bool:
        """
        Return True if we're working with a known Smarter environment, and
        we consider it safe to create billable resources in AWS.

        :return: True if ready
        :rtype: bool
        """
        if not isinstance(self.identity, dict):
            return False
        return True

    @property
    def authentication_credentials_state(self) -> str:
        """
        Return formatted ready state.

        :return: formatted ready state
        :rtype: str
        """
        if self.authentication_credentials_are_initialized:
            return self.formatted_state_ready
        else:
            return self.formatted_state_not_ready
