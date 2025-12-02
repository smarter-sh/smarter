"""AWS IAM helper class."""

# python stuff

from smarter.common.conf import settings as smarter_settings

from .aws import AWSBase, SmarterAWSException


# our stuff


class AWSIdentifyAccessManagement(AWSBase):
    """
    Provides a high-level interface for managing AWS Identity and Access Management (IAM) resources.

    This helper class abstracts common operations related to AWS IAM, such as retrieving IAM policies and roles,
    and managing connections to the IAM service. It simplifies interactions with the AWS IAM API by encapsulating
    client initialization and error handling, making it easier to integrate IAM management into automation workflows
    or larger AWS orchestration systems.

    The class is designed to work with application configuration settings and ensures that AWS sessions are properly
    initialized before performing any operations. It supports robust and maintainable code by providing logging and
    exception handling for operations involving IAM resources, such as policies and roles, within AWS environments.
    """

    _client = None

    @property
    def client(self):
        """
        Return the AWS IAM client.

        :return: boto3 IAM client
        :rtype: boto3.client
        """
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("iam")
        return self._client

    def get_iam_policies(self):
        """
        Return a dict of the AWS IAM policies.

        :return: A dict of IAM policies.
        :rtype: dict
        """
        policies = self.client.list_policies()["Policies"]
        retval = {}
        for policy in policies:
            if smarter_settings.shared_resource_identifier in policy["PolicyName"]:
                policy_version = self.client.get_policy(PolicyArn=policy["Arn"])["Policy"]["DefaultVersionId"]
                policy_document = self.client.get_policy_version(PolicyArn=policy["Arn"], VersionId=policy_version)[
                    "PolicyVersion"
                ]["Document"]
                retval[policy["PolicyName"]] = {"Arn": policy["Arn"], "Policy": policy_document}
        return retval

    def get_iam_roles(self):
        """
        Return a dict of the AWS IAM roles.

        :return: A dict of IAM roles.
        :rtype: dict
        """
        roles = self.client.list_roles()["Roles"]
        retval = {}
        for role in roles:
            if smarter_settings.shared_resource_identifier in role["RoleName"]:
                attached_policies = self.client.list_attached_role_policies(RoleName=role["RoleName"])[
                    "AttachedPolicies"
                ]
                retval[role["RoleName"]] = {
                    "Arn": role["Arn"],
                    "Role": role,
                    "AttachedPolicies": attached_policies,
                }
        return retval or {}
