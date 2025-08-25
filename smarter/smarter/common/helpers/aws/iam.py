"""AWS IAM helper class."""

# python stuff

from smarter.common.conf import settings as smarter_settings

from .aws import AWSBase, SmarterAWSException


# our stuff


class AWSIdentifyAccessManagement(AWSBase):
    """AWS IAM helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS IAM client."""
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("iam")
        return self._client

    def get_iam_policies(self):
        """Return a dict of the AWS IAM policies."""
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
        """Return a dict of the AWS IAM roles."""
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
