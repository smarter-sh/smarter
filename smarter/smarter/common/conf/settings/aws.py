# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The AWS settings: credentials, region, the EKS cluster, and the LLMHost node group."""

import logging
import re
from typing import List, Optional, Union

from pydantic import BaseModel, Field, SecretStr, ValidationInfo

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.env import DEFAULT_MISSING_VALUE, is_missing_value
from smarter.common.conf.services import AWS_REGIONS, services
from smarter.common.conf.util import before_field_validator
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError

logger = logging.getLogger(__name__)

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


class AwsSettings(BaseModel):
    """The cloud provider: AWS credentials, region, and the EKS cluster."""

    aws_profile: Optional[str] = Field(
        settings_defaults.AWS_PROFILE,
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
    :default: Value from ``settings_defaults.AWS_PROFILE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("aws_profile")
    def validate_aws_profile(cls, v: Optional[str]) -> Optional[str]:
        """Validates the `aws_profile` field.

        Uses settings_defaults if no value is received.

        Args:
            v (Optional[str]): The AWS profile value to validate.

        Returns:
            Optional[str]: The validated AWS profile.
        """
        if v in THE_EMPTY_SET:
            if settings_defaults.AWS_PROFILE == DEFAULT_MISSING_VALUE:
                return None
            return settings_defaults.AWS_PROFILE
        return v

    aws_access_key_id: Optional[SecretStr] = Field(
        settings_defaults.AWS_ACCESS_KEY_ID,
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
    :default: Value from ``settings_defaults.AWS_ACCESS_KEY_ID``
    :raises SmarterConfigurationError: If the value is not a valid AWS access key ID
    """

    @before_field_validator("aws_access_key_id")
    def validate_aws_access_key_id(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_access_key_id` field.

        Uses settings_defaults if no value is received.

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
        settings_defaults.AWS_SECRET_ACCESS_KEY,
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
    :default: Value from ``settings_defaults.AWS_SECRET_ACCESS_KEY``
    :raises SmarterConfigurationError: If the value is not a valid AWS secret access key
    """

    @before_field_validator("aws_secret_access_key")
    def validate_aws_secret_access_key(cls, v: Optional[SecretStr], values: ValidationInfo) -> Optional[SecretStr]:
        """Validates the `aws_secret_access_key` field.

        Uses settings_defaults if no value is received.

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

    aws_region: Optional[str] = Field(
        settings_defaults.AWS_REGION,
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
    :default: Value from ``settings_defaults.AWS_REGION``
    :raises SmarterConfigurationError: If the value is not a valid AWS region name.
    """

    @before_field_validator("aws_region")
    def validate_aws_region(cls, v: Optional[str], values: ValidationInfo, **kwargs) -> Optional[str]:
        """Validates the `aws_region` field.

        Uses settings_defaults if no value is received.

        Args:
            v (Optional[str]): The AWS region value to validate.
            values (ValidationInfo): The validation info containing other field values.

        Returns:
            Optional[str]: The validated AWS region.
        """

        valid_regions = values.data.get("aws_regions", AWS_REGIONS)
        if v in THE_EMPTY_SET:
            if settings_defaults.AWS_REGION == DEFAULT_MISSING_VALUE:
                return None
            return settings_defaults.AWS_REGION
        if v not in valid_regions:
            raise SmarterValueError(f"aws_region {v} not in aws_regions: {valid_regions}")
        return v

    @property
    def aws_is_configured(self) -> bool:
        """
        True if AWS is configured.

        This is determined by the presence of either AWS_PROFILE or both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.
        This setting indicates whether the platform has sufficient AWS credentials
        configured to connect to AWS services. If AWS is not configured, attempts
        to use AWS services will fail.

        :type: bool
        """
        logger.debug("Checking if AWS is configured with aws_profile, or aws_access_key_id and aws_secret_access_key.")
        return services.is_connected_to_aws()

    platform_cloud_provider: str = Field(
        settings_defaults.PLATFORM_CLOUD_PROVIDER,
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
    :default: ``aws``, from ``settings_defaults.PLATFORM_CLOUD_PROVIDER``
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
            return settings_defaults.PLATFORM_CLOUD_PROVIDER
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"cloud_provider of type {type(v)} is not a str.")
        return v.strip().lower()

    subsystem_k8s_cluster_name: Optional[str] = Field(
        settings_defaults.SUBSYSTEM_K8S_CLUSTER_NAME,
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
    :default: Value from ``settings_defaults.SUBSYSTEM_K8S_CLUSTER_NAME``, None if it is not set.
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
            v = settings_defaults.SUBSYSTEM_K8S_CLUSTER_NAME
        if is_missing_value(v):
            return None

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"k8s_cluster_name of type {type(v)} is not a str.")

        return v

    app_llmhost_node_role_arn: Optional[str] = Field(
        settings_defaults.APP_LLMHOST_NODE_ROLE_ARN,
        description="The IAM role of the node groups that Smarter creates for LLMHosts.",
        examples=["arn:aws:iam::123456789012:role/eks-node-role"],
        title="LLMHost Node Role ARN",
    )
    """
    The IAM role of the EKS managed node groups that Smarter creates for LLMHostCompute.

    If it is not set, Smarter uses the node role of the cluster's first managed node group
    that it did not create, i.e. the node group that Smarter itself runs on.

    :type: Optional[str]
    :default: Value from ``settings_defaults.APP_LLMHOST_NODE_ROLE_ARN``
    """

    app_llmhost_node_subnet_ids: List[str] = Field(
        settings_defaults.APP_LLMHOST_NODE_SUBNET_IDS,
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
    :default: Value from ``settings_defaults.APP_LLMHOST_NODE_SUBNET_IDS``
    """

    @before_field_validator("app_llmhost_node_subnet_ids")
    def validate_app_llmhost_node_subnet_ids(cls, v: Optional[Union[List[str], str]]) -> List[str]:
        """Validates the `llmhost_node_subnet_ids` field: a list, or a comma-separated string."""
        if v in THE_EMPTY_SET:
            return []
        if isinstance(v, str):
            return [subnet.strip() for subnet in v.split(",") if subnet.strip()]
        if not isinstance(v, list):
            raise SmarterConfigurationError(f"llmhost_node_subnet_ids of type {type(v)} is not a list.")
        return [str(subnet) for subnet in v]


__all__ = ["AwsSettings"]
