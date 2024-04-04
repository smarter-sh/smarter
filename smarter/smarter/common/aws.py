# -*- coding: utf-8 -*-
"""A utility class for introspecting AWS infrastructure."""

# python stuff
import logging
import os
import socket
import time

# our stuff
from .conf import Services
from .conf import settings as smarter_settings
from .utils import recursive_sort_dict


logger = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class AWSInfrastructureConfig:
    """AWS Infrastructure Config"""

    _domain = None

    @property
    def dump(self):
        """Return a dict of the AWS infrastructure config."""
        retval = {}
        if Services.enabled(Services.AWS_APIGATEWAY):
            api = self.get_api(smarter_settings.aws_apigateway_name)
            retval["apigateway"] = {
                "api_id": api.get("id"),
                "stage": self.get_api_stage(),
                "domains": self.get_api_custom_domains(),
            }
        if Services.enabled(Services.AWS_S3):
            retval["s3"] = {"bucket_name": self.get_bucket_by_prefix(smarter_settings.aws_s3_bucket_name)}
        if Services.enabled(Services.AWS_DYNAMODB):
            retval["dynamodb"] = {"table_name": self.get_dyanmodb_table_by_name(smarter_settings.aws_dynamodb_table_id)}
        if Services.enabled(Services.AWS_REKOGNITION):
            retval["rekognition"] = {
                "collection_id": self.get_rekognition_collection_by_id(smarter_settings.aws_rekognition_collection_id)
            }
        if Services.enabled(Services.AWS_IAM):
            retval["iam"] = {"policies": self.get_iam_policies(), "roles": self.get_iam_roles()}
        if Services.enabled(Services.AWS_LAMBDA):
            retval["lambda"] = self.get_lambdas()
        if Services.enabled(Services.AWS_ROUTE53) and Services.enabled(Services.AWS_APIGATEWAY):
            retval["route53"] = self.get_dns_record_from_hosted_zone()
        return recursive_sort_dict(retval)

    def get_lambdas(self):
        """Return a dict of the AWS Lambdas."""
        lambda_client = smarter_settings.aws_session.client("lambda")
        lambdas = lambda_client.list_functions()["Functions"]
        retval = {
            lambda_function["FunctionName"]: lambda_function["FunctionArn"]
            for lambda_function in lambdas
            if smarter_settings.shared_resource_identifier in lambda_function["FunctionName"]
        }
        return retval or {}

    def get_iam_policies(self):
        """Return a dict of the AWS IAM policies."""
        iam_client = smarter_settings.aws_session.client("iam")
        policies = iam_client.list_policies()["Policies"]
        retval = {}
        for policy in policies:
            if smarter_settings.shared_resource_identifier in policy["PolicyName"]:
                policy_version = iam_client.get_policy(PolicyArn=policy["Arn"])["Policy"]["DefaultVersionId"]
                policy_document = iam_client.get_policy_version(PolicyArn=policy["Arn"], VersionId=policy_version)[
                    "PolicyVersion"
                ]["Document"]
                retval[policy["PolicyName"]] = {"Arn": policy["Arn"], "Policy": policy_document}
        return retval

    def get_iam_roles(self):
        """Return a dict of the AWS IAM roles."""
        iam_client = smarter_settings.aws_session.client("iam")
        roles = iam_client.list_roles()["Roles"]
        retval = {}
        for role in roles:
            if smarter_settings.shared_resource_identifier in role["RoleName"]:
                attached_policies = iam_client.list_attached_role_policies(RoleName=role["RoleName"])[
                    "AttachedPolicies"
                ]
                retval[role["RoleName"]] = {
                    "Arn": role["Arn"],
                    "Role": role,
                    "AttachedPolicies": attached_policies,
                }
        return retval or {}

    def get_api_stage(self) -> str:
        """Return the API stage."""
        api = self.get_api(smarter_settings.aws_apigateway_name) or {}
        api_id = api.get("id")
        if api_id:
            response = smarter_settings.aws_apigateway_client.get_stages(restApiId=api_id)
            # Assuming you want the most recently deployed stage
            stages = response.get("item", [])
            if stages:
                retval = stages[-1]["stageName"]
                return retval
        return ""

    def get_api_custom_domains(self) -> list:
        """Return the API custom domains."""

        def filter_dicts(lst):
            return [
                d for d in lst if "domainName" in d and smarter_settings.shared_resource_identifier in d["domainName"]
            ]

        response = smarter_settings.aws_apigateway_client.get_domain_names()
        retval = response.get("items", [])
        return filter_dicts(retval)

    def get_url(self, path) -> str:
        """Return the url for the given path."""
        if smarter_settings.aws_apigateway_create_custom_domaim:
            return f"https://{smarter_settings.aws_apigateway_domain_name}{path}"
        return f"https://{smarter_settings.aws_apigateway_domain_name}/{self.get_api_stage()}{path}"

    def aws_connection_works(self):
        """Test that the AWS connection works."""
        try:
            # pylint: disable=pointless-statement
            smarter_settings.aws_session.region_name
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    @property
    def domain(self):
        """Return the domain."""
        if not self._domain:
            if smarter_settings.aws_apigateway_create_custom_domaim:
                self._domain = (
                    os.getenv(key="DOMAIN")
                    or "api." + smarter_settings.shared_resource_identifier + "." + smarter_settings.root_domain
                )
                return self._domain

            response = smarter_settings.aws_apigateway_client.get_rest_apis()
            for item in response["items"]:
                if item["name"] == self.api_gateway_name:
                    api_id = item["id"]
                    self._domain = f"{api_id}.execute-api.{smarter_settings.aws_region}.amazonaws.com"
        return self._domain

    @property
    def api_gateway_name(self):
        """Return the API Gateway name."""
        return smarter_settings.shared_resource_identifier + "-api"

    def domain_exists(self) -> bool:
        """Test that the domain exists."""
        try:
            socket.gethostbyname(smarter_settings.aws_apigateway_domain_name)
            return True
        except socket.gaierror:
            return False

    def get_bucket_by_prefix(self, bucket_prefix) -> str:
        """Return the bucket name given the bucket prefix."""
        try:
            for bucket in smarter_settings.aws_s3_client.list_buckets()["Buckets"]:
                if bucket["Name"].startswith(bucket_prefix):
                    return f"arn:aws:s3:::{bucket['Name']}"
        except TypeError:
            # TypeError: startswith first arg must be str or a tuple of str, not NoneType
            pass
        return None

    def bucket_exists(self, bucket_prefix) -> bool:
        """Test that the S3 bucket exists."""
        bucket = self.get_bucket_by_prefix(bucket_prefix)
        return bucket is not None

    def get_dyanmodb_table_by_name(self, table_name) -> str:
        """Return the DynamoDB table given the table name."""
        response = smarter_settings.aws_dynamodb_client.list_tables()
        for table in response["TableNames"]:
            if table == table_name:
                table_description = smarter_settings.aws_dynamodb_client.describe_table(TableName=table_name)
                return table_description["Table"]["TableArn"]
        return None

    def dynamodb_table_exists(self, table_name) -> bool:
        """Test that the DynamoDB table exists."""
        table = self.get_dyanmodb_table_by_name(table_name)
        return table is not None

    def api_exists(self, api_name: str) -> bool:
        """Test that the API Gateway exists."""
        response = smarter_settings.aws_apigateway_client.get_rest_apis()

        for item in response["items"]:
            if item["name"] == api_name:
                return True
        return False

    def get_api(self, api_name: str) -> dict:
        """Test that the API Gateway exists."""
        response = smarter_settings.aws_apigateway_client.get_rest_apis()

        for item in response["items"]:
            if item["name"] == api_name:
                return item
        return {}

    def api_resource_and_method_exists(self, path, method) -> bool:
        """Test that the API Gateway resource and method exists."""
        api = self.get_api(smarter_settings.aws_apigateway_name) or {}
        api_id = api.get("id")
        resources = smarter_settings.aws_apigateway_client.get_resources(restApiId=api_id)
        for resource in resources["items"]:
            if resource["path"] == path:
                try:
                    smarter_settings.aws_apigateway_client.get_method(
                        restApiId=api_id, resourceId=resource["id"], httpMethod=method
                    )
                    return True
                except smarter_settings.aws_apigateway_client.exceptions.NotFoundException:
                    return False

        return False

    def get_api_keys(self) -> str:
        """Test that the API Gateway exists."""
        response = smarter_settings.aws_apigateway_client.get_api_keys(includeValues=True)
        for item in response["items"]:
            if item["name"] == smarter_settings.shared_resource_identifier:
                return item["value"]
        return False

    def get_rekognition_collection_by_id(self, collection_id) -> str:
        """Return the Rekognition collection."""
        response = smarter_settings.aws_rekognition_client.list_collections()
        for collection in response["CollectionIds"]:
            if collection == collection_id:
                return collection
        return None

    def rekognition_collection_exists(self) -> bool:
        """Test that the Rekognition collection exists."""
        collection = self.get_rekognition_collection_by_id(smarter_settings.aws_rekognition_collection_id)
        return collection is not None

    def get_hosted_zone(self, domain_name) -> str:
        """Return the hosted zone."""
        response = smarter_settings.aws_route53_client.list_hosted_zones()
        for hosted_zone in response["HostedZones"]:
            if hosted_zone["Name"] == domain_name or hosted_zone["Name"] == f"{domain_name}.":
                return hosted_zone
        return None

    def get_or_create_hosted_zone(self, domain_name) -> str:
        """
        Return the hosted zone.
        example return:
            {
                'HostedZone': {
                    'Id': '/hostedzone/Z148QEXAMPLE8V',
                    'Name': 'example.com.',
                    'CallerReference': 'my hosted zone',
                    'Config': {
                        'Comment': 'This is my hosted zone',
                        'PrivateZone': False
                    },
                    'ResourceRecordSetCount': 2
                },
                'DelegationSet': {
                    'NameServers': [
                        'ns-2048.awsdns-64.com',
                        'ns-2049.awsdns-65.net',
                        'ns-2050.awsdns-66.org',
                        'ns-2051.awsdns-67.co.uk'
                    ]
                }
            }
        """
        hosted_zone = self.get_hosted_zone(domain_name)
        if hosted_zone:
            return (hosted_zone, False)

        smarter_settings.aws_route53_client.create_hosted_zone(
            Name=domain_name,
            CallerReference=str(time.time()),  # Unique string used to identify the request
            HostedZoneConfig={"Comment": "Managed by Smarter", "PrivateZone": False},
        )
        hosted_zone = self.get_hosted_zone(domain_name)
        logger.info("Created hosted zone %s %s", hosted_zone, domain_name)
        return (hosted_zone, True)

    def get_dns_record(self, hosted_zone_id: str, record_name: str, record_type: str) -> str:
        """
        Return the DNS record from the hosted zone.
        example return value:
        {
            "Name": "example.com.",
            "Type": "A",
            "TTL": 300,
            "ResourceRecords": [
                {
                    "Value": "
        """

        def name_match(record_name, record) -> bool:
            return record["Name"] == record_name or record["Name"] == f"{record_name}."

        response = smarter_settings.aws_route53_client.list_resource_record_sets(HostedZoneId=hosted_zone_id)
        for record in response["ResourceRecordSets"]:
            if (
                name_match(record_name=record_name, record=record)
                and str(record["Type"]).upper() == record_type.upper()
            ):
                return record
        return None

    def get_ns_records(self, hosted_zone_id: str):
        """
        Return the NS records from the hosted zone.
        example return value:
        [
            {
                "Value": "ns-2048.awsdns-64.com"
            },
            {
                "Value": "ns-2049.awsdns-65.net"
            },
            {
                "Value": "ns-2050.awsdns-66.org"
            },
            {
                "Value": "ns-2051.awsdns-67.co.uk"
            }
        ]
        """
        response = smarter_settings.aws_route53_client.list_resource_record_sets(HostedZoneId=hosted_zone_id)
        for record in response["ResourceRecordSets"]:
            if record["Type"] == "NS":
                return record["ResourceRecords"]
        return None

    # pylint: disable=too-many-arguments
    def get_or_create_dns_record(
        self,
        hosted_zone_id: str,
        record_name: str,
        record_type: str,
        record_ttl: int,
        record_alias_target: dict = None,
        record_value=None,
    ) -> str:
        def match_values(record_value, record) -> bool:
            record_value = record_value or []
            resource_records = record["ResourceRecords"] if "ResourceRecords" in record else []
            record_values = [item["Value"] for item in resource_records]
            record_value_values = [item["Value"] for item in record_value]
            return set(record_values) == set(record_value_values)

        def match_alias(record_alias_target, record) -> bool:
            """
            Match the alias target
            'AliasTarget': {'HostedZoneId': 'Z3AADJGX6KTTL2', 'DNSName': 'a1db5dfcf202b4a63bdcd0f3c03e769f-769707598.us-east-2.elb.amazonaws.com.', 'EvaluateTargetHealth': True}}
            """
            record_alias = record.get("AliasTarget", None)
            if not record_alias_target and not record_alias:
                return False
            if record_alias_target == record_alias:
                return True
            return False

        record = self.get_dns_record(hosted_zone_id=hosted_zone_id, record_name=record_name, record_type=record_type)
        if record:
            if match_values(record_value, record) or match_alias(record_alias_target, record):
                return record
            logger.info("Updating %s %s record", record_name, record_type)
        else:
            logger.info("Creating %s %s record", record_name, record_type)

        change_batch = {
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": record_type,
                    },
                }
            ]
        }
        if record_alias_target:
            change_batch["Changes"][0]["ResourceRecordSet"]["AliasTarget"] = record_alias_target
        if record_value:
            change_batch["Changes"][0]["ResourceRecordSet"]["ResourceRecords"] = [
                {"Value": item["Value"]} for item in record_value
            ]
            change_batch["Changes"][0]["ResourceRecordSet"]["TTL"] = record_ttl

        smarter_settings.aws_route53_client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=change_batch,
        )
        logger.info("Posting aws route53 change batch %s", change_batch)
        record = self.get_dns_record(hosted_zone_id=hosted_zone_id, record_name=record_name, record_type=record_type)
        logger.info("Posted aws routed53 DNS record %s", change_batch)
        return record

    def get_hosted_zone_id(self, hosted_zone) -> str:
        """Return the hosted zone id."""
        if hosted_zone:
            return hosted_zone["Id"].split("/")[-1]
        return None

    def get_hosted_zone_id_for_domain(self, domain_name) -> str:
        """Return the hosted zone id for the domain."""
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name)
        return self.get_hosted_zone_id(hosted_zone)

    def get_environment_A_record(self, domain: str = None) -> dict:
        """
        Return the DNS A record for the environment domain.
        example return value:
        {
            "Name": "example.com.",
            "Type": "A",
            "TTL": 300,
            "ResourceRecords": [{"Value": "192.1.1.1"}]
        }
        """
        domain = domain or smarter_settings.environment_domain
        hosted_zone, _ = aws_helper.get_or_create_hosted_zone(domain_name=domain)
        hosted_zone_id = aws_helper.get_hosted_zone_id(hosted_zone)
        environment_A_record = aws_helper.get_dns_record(
            hosted_zone_id=hosted_zone_id, record_name=domain, record_type="A"
        )
        return environment_A_record


class SingletonConfig:
    """Singleton for Settings"""

    _instance = None

    def __new__(cls):
        """Create a new instance of Settings"""
        if cls._instance is None:
            cls._instance = super(SingletonConfig, cls).__new__(cls)
            cls._instance._config = AWSInfrastructureConfig()
        return cls._instance

    @property
    def config(self) -> AWSInfrastructureConfig:
        """Return the smarter_settings"""
        return self._config  # pylint: disable=E1101


aws_helper = SingletonConfig().config
