"""AWS helper base class."""

# python stuff
import logging
import os
from urllib.parse import urlparse

import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
from botocore.exceptions import ProfileNotFound

from smarter.common.conf import Services
from smarter.common.conf import settings as smarter_settings

# our stuff
from smarter.common.const import (
    SMARTER_CUSTOMER_API_SUBDOMAIN,
    SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN,
    SmarterEnvironments,
)

# mcdaniel apr-2024: technically we shouldn't import smarter.libe.django into the aws helpers
# but the validators don't depend on django initialization, so we're okay here.
from smarter.lib.django.validators import SmarterValidator, SmarterValueError

from .exceptions import AWSNotReadyError


logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class AWSBase:
    """
    AWS helper base class. Responsible for
    - initializing the AWS connection and ensuring that we don't invoke boto3 until we're in a ready state.
    - detecting if we're inside an AWS environment like AWS Lambda.
    - decision making on whether we're working with a known Smarter environment that we consider safe to create billable resources in AWS.
    - reformatting localhost domain names into proxy domains that will work with AWS Route53 and Kubernetes.
    """

    LOCAL_HOSTS = smarter_settings.local_hosts

    _aws_access_key_id: str = None
    _aws_secret_access_key: str = None
    _aws_region: str = None
    _aws_profile: str = None

    _aws_access_key_id_source: str = None
    _aws_secret_access_key_source: str = None

    _initialized: bool = False
    _domain = None
    _aws_session = None
    _root_domain: str = None
    _environment: str = None
    _environment_domain: str = None
    _shared_resource_identifier: str = None
    _debug_mode: bool = False

    _connected: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        aws_region: str = None,
        aws_profile: str = None,
        shared_resource_identifier: str = None,
        environment: str = None,
        environment_domain: str = None,
        root_domain: str = None,
        debug_mode: bool = False,
        init_info: str = None,
    ):
        Services.raise_error_on_disabled(Services.AWS_CLI)

        self._shared_resource_identifier = shared_resource_identifier or smarter_settings.shared_resource_identifier
        self._environment = environment or smarter_settings.environment

        self._root_domain = root_domain or smarter_settings.root_domain
        self._environment_domain = environment_domain or smarter_settings.environment_domain
        self._debug_mode = debug_mode or smarter_settings.debug_mode

        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
        if init_info:
            logger.debug(init_info)

        # ----------------------------------------------------------------------
        # AWS authentication. Hereon we only want to initialize whatever is
        # needed to establish a connection to AWS.
        # ----------------------------------------------------------------------

        # priority 1: AWS IAM role based security
        if not self.initialized and self.is_aws_deployed:
            # If we're running inside AWS Lambda, then we don't need to set the AWS credentials.
            logger.debug("running inside AWS Lambda")
            self._aws_access_key_id_source: str = "overridden by IAM role-based security"
            self._aws_secret_access_key_source: str = "overridden by IAM role-based security"
            self._aws_session = boto3.Session(region_name=self.aws_region)
            self._initialized = True

        # initialize creentials from smarter_settings unless any of these were passed as parameters
        self._aws_access_key_id = aws_access_key_id or smarter_settings.aws_access_key_id.get_secret_value()
        self._aws_secret_access_key = aws_secret_access_key or smarter_settings.aws_secret_access_key.get_secret_value()
        self._aws_region = aws_region or smarter_settings.aws_region
        self._aws_profile = aws_profile or smarter_settings.aws_profile

        # priority 2: aws_profile
        if not self.initialized:
            if self.aws_profile:
                self._aws_access_key_id_source = "aws_profile"
                self._aws_secret_access_key_source = "aws_profile"
                self._initialized = True

        # priority 3: aws_access_key_id and aws_secret_access_key
        if not self.initialized and self.aws_access_key_id and self.aws_secret_access_key and self.aws_region:
            self._aws_session = boto3.Session(
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
            self._initialized = True
            self._aws_access_key_id_source = "passed parameter"
            self._aws_secret_access_key_source = "passed parameter"

        logger.debug("initialized settings: %s", self.aws_auth)
        if not self.ready():
            msg = f"Unable to initialize AWSBase for environment {self.environment}."
            if self.environment not in SmarterEnvironments.aws_environments:
                msg += f" Please note AWS classes only work with the following environments: {SmarterEnvironments.aws_environments}"
            raise AWSNotReadyError(msg)

    @property
    def debug_mode(self):
        """Debug mode"""
        return self._debug_mode

    @property
    def initialized(self):
        """Is settings initialized?"""
        return self._initialized

    @property
    def is_aws_deployed(self) -> bool:
        """Return True if we're running inside of AWS Lambda."""
        return bool(os.environ.get("AWS_DEPLOYED", False))

    @property
    def aws_profile(self):
        """AWS profile"""
        return self._aws_profile

    @property
    def aws_account_id(self):
        """AWS account id"""
        Services.raise_error_on_disabled(Services.AWS_CLI)
        sts_client = self.aws_session.client("sts")
        if not sts_client:
            logger.warning("could not initialize sts_client")
            return None
        retval = sts_client.get_caller_identity()
        if not isinstance(retval, dict):
            logger.warning("sts_client.get_caller_identity() did not return a dict")
            return None
        return retval.get("Account", None)

    @property
    def aws_region(self):
        """AWS region"""
        return self._aws_region

    @property
    def aws_access_key_id_source(self):
        """AWS access key id source"""
        return self._aws_access_key_id_source

    @property
    def aws_access_key_id(self):
        """AWS access key id"""
        return self._aws_access_key_id

    @property
    def aws_secret_access_key_source(self):
        """AWS secret access key source"""
        return self._aws_secret_access_key_source

    @property
    def aws_secret_access_key(self):
        """AWS secret access key"""
        return self._aws_secret_access_key

    @property
    def aws_auth(self) -> dict:
        """AWS authentication"""
        retval = {
            "aws_profile": self.aws_profile,
            "aws_access_key_id_source": self.aws_access_key_id_source,
            "aws_secret_access_key_source": self.aws_secret_access_key_source,
            "aws_region": self.aws_region,
        }
        return retval

    @property
    def aws_session(self):
        """AWS session"""
        if not self._aws_session:
            if self.aws_profile:
                logger.debug("creating new aws_session with aws_profile: %s", self.aws_profile)
                try:
                    self._aws_session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
                except ProfileNotFound:
                    logger.warning("aws_profile %s not found", self.aws_profile)

                return self._aws_session
            if self.aws_access_key_id is not None and self.aws_secret_access_key is not None:
                logger.debug("creating new aws_session with aws keypair: %s", self.aws_access_key_id_source)
                self._aws_session = boto3.Session(
                    region_name=self.aws_region,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                )
                return self._aws_session
            logger.debug("creating new aws_session without aws credentials")
            self._aws_session = boto3.Session(region_name=self.aws_region)
        return self._aws_session

    @property
    def shared_resource_identifier(self):
        """Return the shared resource identifier."""
        return self._shared_resource_identifier

    @property
    def environment(self) -> str:
        """Return the environment."""
        return self._environment

    @property
    def environment_domain(self) -> str:
        """
        we need to rebuild these in order to reformat the localhost domain into
        a proxy domain that will work with AWS Route53 and Kubernetes
        """
        return f"{self.environment}.{SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN}.{self.root_domain}"

    @property
    def customer_api_domain(self) -> str:
        """
        we need to rebuild these in order to reformat the localhost domain into
        a proxy domain that will work with AWS Route53 and Kubernetes
        """
        return f"{self.environment}.{SMARTER_CUSTOMER_API_SUBDOMAIN}.{self.root_domain}"

    @property
    def root_domain(self) -> str:
        """Return the root domain."""
        return self._root_domain

    # --------------------------------------------------------------------------
    # helper functions
    # --------------------------------------------------------------------------
    def domain_resolver(self, domain: str) -> str:
        """Validate the domain and swap out localhost for the proxy domain."""
        if self.environment == SmarterEnvironments.LOCAL:
            proxy_domain: str = None
            if smarter_settings.environment_domain in domain:
                proxy_domain = domain.replace(smarter_settings.environment_domain, self.environment_domain)
            if smarter_settings.customer_api_domain in domain:
                proxy_domain = domain.replace(smarter_settings.customer_api_domain, self.customer_api_domain)
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
    def ready(self) -> bool:
        """
        Return True if we're working with a known Smarter environment, and
        we consider it safe to create billable resources in AWS.
        """
        return self.connected() and smarter_settings.environment in SmarterEnvironments.all

    def connected(self):
        """Test that the AWS connection works."""
        if self._connected:
            return True
        try:
            # pylint: disable=pointless-statement
            self._connected = self.aws_session.client("sts").get_caller_identity()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("connected() Failure - %s", e)
        return self._connected
