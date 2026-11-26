# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The AWS settings: credentials, region, the EKS cluster, and the LLMHost node group."""

import re
from typing import List, Optional, Union

import boto3
from botocore.exceptions import (
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, ValidationInfo

from smarter.common.conf.const import DEFAULT_MISSING_VALUE, THE_EMPTY_SET
from smarter.common.conf.env import is_missing_value
from smarter.common.conf.util import (
    before_field_validator,
    comma_separated,
    field_default,
)
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)

STATIC_AWS_KEY_PAIR_WARNING = (
    "SECURITY WARNING: a static AWS key pair is configured (%s, from AWS_ACCESS_KEY_ID and "
    "AWS_SECRET_ACCESS_KEY). This is a security risk, and it is not recommended. A key pair never "
    "expires: it sits in every pod's environment and in the Helm release's Secret, and anyone who "
    "obtains it can use the AWS account from anywhere until it is revoked. Prefer IAM role-based "
    "credentials. On Kubernetes, that is IAM Roles for Service Accounts (IRSA), which the "
    "smarter-infrastructure Terraform modules create for each environment "
    "(aws/terraform/smarter/iam-irsa.tf: the smarter and smarter-backup roles, scoped to the "
    "platform's own permissions), and which the Helm chart assumes through serviceAccount.awsRoleArn "
    "and databaseScheduledBackup.awsRoleArn. Each pod then gets short-lived credentials that AWS "
    "rotates automatically, and that nothing stores. A key pair takes precedence over the role, so "
    "once the role is in place, remove AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from the "
    "chart's env and from .env. For local development, prefer an AWS profile (AWS_PROFILE, e.g. "
    "with AWS IAM Identity Center) to a long-lived key pair."
)
"""The warning that a real AWS key pair is configured: %s is the setting's name, never its value."""

AWS_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "af-south-1",
    "ap-east-1",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-south-1",
    "ap-south-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-southeast-3",
    "ap-southeast-4",
    "ap-southeast-5",
    "ap-southeast-7",
    "ca-central-1",
    "ca-west-1",
    "eu-central-1",
    "eu-central-2",
    "eu-north-1",
    "eu-south-1",
    "eu-south-2",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "il-central-1",
    "me-central-1",
    "me-south-1",
    "mx-central-1",
    "sa-east-1",
]
"""
The AWS commercial regions, the default of ``aws_regions``, against which ``aws_region`` is validated.

It includes the regions that an account must opt in to. To use a region that isn't listed, e.g. a new one or
a GovCloud region, set ``aws_regions``.
"""

_warned_static_aws_key_pair = False
"""Whether this process has logged :data:`STATIC_AWS_KEY_PAIR_WARNING`, which it logs once."""


def warn_static_aws_key_pair(field_name: str) -> None:
    """
    Log, once per process, that a real AWS key pair is configured, and why an IAM role is preferred.

    The access key id and the secret access key are validated one after the other, and both are set
    together, so the pair is reported once. The log names the setting, never its value.

    :param field_name: The setting that holds a key, e.g. ``aws_access_key_id``.
    """
    global _warned_static_aws_key_pair  # pylint: disable=global-statement
    if _warned_static_aws_key_pair:
        return
    _warned_static_aws_key_pair = True
    logger.warning(STATIC_AWS_KEY_PAIR_WARNING, f"smarter_settings.{field_name}")


def aws_credentials_work() -> bool:
    """
    Whether AWS credentials are available, and AWS accepts them.

    Calls ``sts.get_caller_identity()``, which every principal may call. It logs a warning, never the
    credentials, when they are missing or rejected.

    :returns: True if the call succeeds.
    """
    session = boto3.Session()
    credentials = session.get_credentials()
    if not credentials:
        logger.warning("AWS is not configured properly. Credentials are invalid, or no credentials were found.")
        return False
    try:
        sts = session.client("sts")
        sts.get_caller_identity()
    except (NoCredentialsError, ProfileNotFound, EndpointConnectionError):
        logger.warning("AWS is not configured properly. Credentials are invalid, or no credentials were found.")
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("Failed to connect to AWS: %s", type(e).__name__)
        return False
    return True


class AwsSettings(BaseModel):
    """The cloud provider: AWS credentials, region, and the EKS cluster."""

    _aws_is_configured: Optional[bool] = PrivateAttr(default=None)
    """The answer of :attr:`aws_is_configured`, once it has asked STS, or None before."""

    aws_profile: Optional[str] = Field(
        None,
        validation_alias="AWS_PROFILE",
        description="The AWS profile to use for authentication. If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.",
        examples=["default", "smarter-profile"],
        title="AWS Profile",
    )
    """
    The AWS profile to use for authentication.

    If present, this will take precedence over AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
    This setting specifies which AWS credentials profile to use when connecting to AWS services.
    Profiles are defined in the AWS credentials file (typically located at ~/.aws/credentials)
    and allow for managing multiple sets of credentials for different environments or accounts.

    :type: Optional[str]
    :default: ``None``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_profile")
    def validate_aws_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `aws_profile` field.

        Uses the field's default if no value is received.

        Args:
            v (Optional[str]): The AWS profile value to validate.

        Returns:
            Optional[str]: The validated AWS profile.
        """
        if v in THE_EMPTY_SET:
            if field_default(cls, "aws_profile") == DEFAULT_MISSING_VALUE:
                return None
            return field_default(cls, "aws_profile")
        return v

    aws_access_key_id: Optional[SecretStr] = Field(
        None,
        validation_alias="AWS_ACCESS_KEY_ID",
        description="The AWS access key ID for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^AKIA[0-9A-Z]{16}$"],
        title="AWS Access Key ID",
    )
    """
    The AWS access key ID for authentication.

    Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the access key ID used to authenticate with AWS services.
    It is used in conjunction with the AWS secret access key to sign requests to AWS APIs.

    :type: SecretStr
    :default: ``None``
    :raises SmarterConfigurationError: If the value is not a valid AWS access key ID
    """

    @before_field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_access_key_id` field.

        Uses the field's default if no value is received.

        Args:
            v (Optional[SecretStr]): The AWS access key ID value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS access key ID.
        """
        if v is None:
            return None
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_access_key_id value to SecretStr")

        if v.get_secret_value() in [None, "", DEFAULT_MISSING_VALUE]:
            return None
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != DEFAULT_MISSING_VALUE:
            logger.warning("aws_access_key_id is being ignored. using aws_profile %s.", aws_profile)
            return None

        # validate the pattern of the access key id
        pattern = r"^AKIA[0-9A-Z]{16}$"
        if not re.match(pattern, v.get_secret_value()):
            raise SmarterConfigurationError("aws_access_key_id is not a valid AWS access key ID format.")

        warn_static_aws_key_pair("aws_access_key_id")
        return v

    aws_secret_access_key: Optional[SecretStr] = Field(
        None,
        validation_alias="AWS_SECRET_ACCESS_KEY",
        description="The AWS secret access key for authentication. Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.",
        examples=["^[0-9a-zA-Z/+]{40}$"],
        title="AWS Secret Access Key",
    )
    """
    The AWS secret access key for authentication.

    Used if AWS_PROFILE is not set. Masked by pydantic SecretStr.
    This setting provides the secret access key used to authenticate with AWS services.
    It is used in conjunction with the AWS access key ID to sign requests to AWS APIs.

    :type: SecretStr
    :default: ``None``
    :raises SmarterConfigurationError: If the value is not a valid AWS secret access key
    """

    @before_field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_secret_access_key` field.

        Uses the field's default if no value is received.

        Args:
            v (Optional[SecretStr]): The AWS secret access key value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            SecretStr: The validated AWS secret access key.
        """
        if v is None:
            return None
        if isinstance(v, str):
            v = SecretStr(v)
        if not isinstance(v, SecretStr):
            raise SmarterConfigurationError("could not convert aws_secret_access_key value to SecretStr")

        if v.get_secret_value() in [None, "", DEFAULT_MISSING_VALUE]:
            return None
        aws_profile = values.data.get("aws_profile", None)
        if aws_profile and len(aws_profile) > 0 and aws_profile != DEFAULT_MISSING_VALUE:
            logger.warning("aws_secret_access_key is being ignored. using aws_profile %s.", aws_profile)
            return None

        # validate the pattern of the secret access key
        pattern = r"^[0-9a-zA-Z/+]{40}$"
        if not re.match(pattern, v.get_secret_value()):
            raise SmarterConfigurationError("aws_secret_access_key is not a valid AWS secret access key format.")

        warn_static_aws_key_pair("aws_secret_access_key")
        return v

    aws_regions: List[str] = Field(
        AWS_REGIONS,
        description="A list of AWS regions considered valid for this platform.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
        title="AWS Regions",
    )
    """
    A list of AWS regions considered valid for this platform.

    This setting defines the AWS regions that the platform is configured to operate in.
    It can be used to restrict operations to specific regions, ensuring that resources
    are created and managed only in approved locations.

    :type: List[str]
    :default: Value from ``AWS_REGIONS``
    :raises SmarterConfigurationError: If the value is not a list of valid AWS region names.
    """

    @before_field_validator("aws_regions")
    def validate_aws_regions(cls, v: Optional[Union[List[str], str]]) -> List[str]:
        """Validates the `aws_regions` field: a list, or a comma-separated string.

        Args:
            v: The regions.
        Returns:
            List[str]: The regions, or the default if it is empty.
        """
        if v in THE_EMPTY_SET:
            return list(AWS_REGIONS)
        v = comma_separated(v)
        if not isinstance(v, list):
            raise SmarterConfigurationError(f"aws_regions of type {type(v)} is not a list.")
        return [str(region) for region in v]

    aws_region: Optional[str] = Field(
        None,
        validation_alias="AWS_REGION",
        description="The single AWS region in which all AWS service clients will operate.",
        examples=["us-east-1", "us-west-2", "eu-west-1"],
        title="AWS Region",
    )
    """
    The single AWS region in which all AWS service clients will operate.

    This setting specifies the default AWS region for the platform.
    All AWS service clients will be configured to use this region unless
    overridden on a per-client basis.

    :type: str
    :default: ``None``
    :raises SmarterConfigurationError: If the value is not a valid AWS region name.
    """

    @before_field_validator("aws_region")
    def validate_aws_region(cls, v: Optional[str], values: ValidationInfo, **kwargs) -> Optional[str]:
        """Validates the `aws_region` field.

        Uses the field's default if no value is received.

        Args:
            v (Optional[str]): The AWS region value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            Optional[str]: The validated AWS region.
        """

        valid_regions = values.data.get("aws_regions", AWS_REGIONS)
        if v in THE_EMPTY_SET:
            if field_default(cls, "aws_region") == DEFAULT_MISSING_VALUE:
                return None
            return field_default(cls, "aws_region")
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    @property
    def aws_is_configured(self) -> bool:
        """
        True if AWS is configured: boto3 finds credentials, and STS accepts them.

        boto3's default credential chain finds them: on Kubernetes, the IAM role of the pod's
        ServiceAccount (IRSA); locally, an AWS profile (``AWS_PROFILE``); or a static key pair
        (``AWS_ACCESS_KEY_ID`` and ``AWS_SECRET_ACCESS_KEY``), which is not recommended. If AWS is
        not configured, attempts to use AWS services will fail.

        STS is asked once, by :meth:`ready` when the settings are created, and the answer is kept:
        the Django settings read it several times as they load, e.g. to choose the storage backend,
        and each read would otherwise be a call to STS, and a warning when it fails.

        :type: bool
        """
        if self._aws_is_configured is None:
            logger.debug("Checking whether boto3 finds AWS credentials, and STS accepts them.")
            self._aws_is_configured = aws_credentials_work()
        return self._aws_is_configured

    platform_cloud_provider: str = Field(
        "aws",
        description="The cloud provider of the platform's infrastructure services: DNS, TLS certificates, and the Kubernetes cluster's credentials.",
        examples=["aws", "memory"],
        title="Cloud Provider",
    )
    """
    The cloud provider of the platform's infrastructure services.

    The platform reaches DNS, TLS certificates, and its Kubernetes cluster's credentials only
    through :mod:`smarter.apps.infrastructure.services`, which uses this provider. ``aws`` is the
    only cloud that is implemented. ``memory`` keeps everything in memory, for local development
    without a cloud account.

    :type: str
    :default: ``aws``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("platform_cloud_provider")
    def validate_platform_cloud_provider(cls, v: Optional[str]) -> str:
        """Validates the `cloud_provider` field.

        Args:
            v (Optional[str]): The cloud provider's name.

        Returns:
            str: The validated cloud provider's name, in lower case.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "platform_cloud_provider")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"cloud_provider of type {type(v)} is not a str.")
        return v.strip().lower()

    subsystem_k8s_cluster_name: Optional[str] = Field(
        None,
        description="The name of the Kubernetes cluster that hosts the platform, e.g. its EKS cluster on AWS.",
        examples=["apps-hosting-service"],
        title="Kubernetes Cluster Name",
    )
    """
    The name of the Kubernetes cluster that hosts the platform: ``SMARTER_SUBSYSTEM_K8S_CLUSTER_NAME``.

    The platform deploys LLMClients and LLMHosts to it. On AWS it is an EKS cluster in the
    configured account, which the AWS infrastructure provider describes to build its kubeconfig.

    It is optional. Without it, the platform runs, but LLMClients and LLMHosts are not
    deployed to Kubernetes, and the first attempt to reach the cluster logs how to set it.

    :type: Optional[str]
    :default: None if it is not set.
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("subsystem_k8s_cluster_name")
    def validate_subsystem_k8s_cluster_name(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `k8s_cluster_name` field.

        Args:
            v (Optional[str]): The Kubernetes cluster name value to validate.

        Returns:
            Optional[str]: The validated cluster name, or None if it is missing or a placeholder.
        """
        if v in THE_EMPTY_SET:
            v = field_default(cls, "subsystem_k8s_cluster_name")
        if is_missing_value(v):
            return None

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"k8s_cluster_name of type {type(v)} is not a str.")

        return v

    app_llmhost_node_role_arn: Optional[str] = Field(
        None,
        description="The IAM role of the node groups that Smarter creates for LLMHosts.",
        examples=["arn:aws:iam::123456789012:role/eks-node-role"],
        title="LLMHost Node Role ARN",
    )
    """
    The IAM role of the EKS managed node groups that Smarter creates for LLMHostCompute.

    If it is not set, Smarter uses the node role of the cluster's first managed node group
    that it did not create, i.e. the node group that Smarter itself runs on.

    :type: Optional[str]
    :default: ``None``
    """

    app_llmhost_node_subnet_ids: List[str] = Field(
        [],
        description="The subnets of the node groups that Smarter creates for LLMHosts.",
        examples=[["subnet-0123456789abcdef0"]],
        title="LLMHost Node Subnet IDs",
    )
    """
    The subnets of the EKS managed node groups that Smarter creates for LLMHostCompute, e.g.

    ``subnet-0123,subnet-0456``. An LLMHostCompute's own subnet_ids take precedence.

    If it is not set, Smarter uses the subnets of the cluster's first managed node group that it
    did not create. A model volume is an EBS volume in one availability zone, so an LLMHost
    whose retained volume is in one zone cannot be relaunched on a node in another: one subnet
    per node group avoids this.

    :type: List[str]
    :default: ``[]``
    """

    @before_field_validator("app_llmhost_node_subnet_ids")
    def validate_app_llmhost_node_subnet_ids(cls, v: Optional[Union[List[str], str]]) -> List[str]:
        """Validates the `llmhost_node_subnet_ids` field: a list, or a comma-separated string."""
        if v in THE_EMPTY_SET:
            return []
        v = comma_separated(v)
        if not isinstance(v, list):
            raise SmarterConfigurationError(f"llmhost_node_subnet_ids of type {type(v)} is not a list.")
        return [str(subnet) for subnet in v]


__all__ = ["AwsSettings"]
