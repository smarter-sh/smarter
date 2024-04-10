# -*- coding: utf-8 -*-
"""AWS Route53 helper class."""

# python stuff
import logging
import time

# our stuff
from .aws import AWSBase


logger = logging.getLogger(__name__)


class AWSRoute53(AWSBase):
    """AWS Route53 helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS Route53 client."""
        if not self._client:
            self._client = self.aws_session.client("route53")
        return self._client

    def get_hosted_zone(self, domain_name) -> str:
        """Return the hosted zone."""
        response = self.client.list_hosted_zones()
        for hosted_zone in response["HostedZones"]:
            if hosted_zone["Name"] == domain_name or hosted_zone["Name"] == f"{domain_name}.":
                return hosted_zone
        return None

    def get_or_create_hosted_zone(self, domain_name) -> tuple[dict, bool]:
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

        self.client.create_hosted_zone(
            Name=domain_name,
            CallerReference=str(time.time()),  # Unique string used to identify the request
            HostedZoneConfig={"Comment": "Managed by Smarter", "PrivateZone": False},
        )
        hosted_zone = self.get_hosted_zone(domain_name)
        logger.info("Created hosted zone %s %s", hosted_zone, domain_name)
        return (hosted_zone, True)

    def delete_hosted_zone(self, domain_name):

        # Get the hosted zone id
        hosted_zone_id = self.get_hosted_zone_id_for_domain(domain_name)

        # Get all record sets
        paginator = self.client.get_paginator("list_resource_record_sets")
        record_sets = []
        for page in paginator.paginate(HostedZoneId=hosted_zone_id):
            for record_set in page["ResourceRecordSets"]:
                if record_set["Type"] not in ["NS", "SOA"]:
                    record_sets.append(record_set)

        # Delete all record sets
        for record_set in record_sets:
            self.client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch={"Changes": [{"Action": "DELETE", "ResourceRecordSet": record_set}]},
            )

        # Delete the hosted zone
        self.client.delete_hosted_zone(Id=hosted_zone_id)

    def get_dns_record(self, hosted_zone_id: str, record_name: str, record_type: str) -> dict:
        """
        Return the DNS record from the hosted zone.
        example return value:
        {
            "Name": "example.com.",
            "Type": "A",
            "TTL": 300,
            "ResourceRecords": [
                {
                    "Value": "192.1.1.1"
                    }
                ]
            }
        """

        def name_match(record_name, record) -> bool:
            return record["Name"] == record_name or record["Name"] == f"{record_name}."

        response = self.client.list_resource_record_sets(HostedZoneId=hosted_zone_id)
        for record in response["ResourceRecordSets"]:
            if (
                name_match(record_name=record_name, record=record)
                and str(record["Type"]).upper() == record_type.upper()
            ):
                logger.info("get_dns_record() found record: %s", record)
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
        response = self.client.list_resource_record_sets(HostedZoneId=hosted_zone_id)
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
        record_value=None,  # can be a single text value of a list of dict
    ) -> dict:
        action: str = None

        def match_values(record_value, fetched_record) -> bool:
            record_value = record_value or []
            if isinstance(record_value, list):
                resource_records = fetched_record.get("ResourceRecords", [])
                record_values = [item["Value"] for item in resource_records]

                record_value_values = [item["Value"] for item in record_value if "Value" in item]
                return set(record_values) == set(record_value_values)
            return False

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

        fetched_record = self.get_dns_record(
            hosted_zone_id=hosted_zone_id, record_name=record_name, record_type=record_type
        )
        if fetched_record:
            if match_values(record_value, fetched_record) or match_alias(record_alias_target, fetched_record):
                logger.info("get_or_create_dns_record() returning matched record: %s", fetched_record)
                return fetched_record
            action = "UPSERT"
            logger.info("Updating %s %s record", record_name, record_type)
        else:
            action = "CREATE"
            logger.info("Creating %s %s record", record_name, record_type)

        change_batch = {
            "Changes": [
                {
                    "Action": action,
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
            if isinstance(record_value, list):
                change_batch["Changes"][0]["ResourceRecordSet"]["ResourceRecords"] = [
                    {"Value": item["Value"]} for item in record_value if "Value" in item
                ]
            else:
                change_batch["Changes"][0]["ResourceRecordSet"]["ResourceRecords"] = [{"Value": f'"{record_value}"'}]
            change_batch["Changes"][0]["ResourceRecordSet"]["TTL"] = record_ttl

        self.client.change_resource_record_sets(
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
        domain = domain or self.environment_domain
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name=domain)
        hosted_zone_id = self.get_hosted_zone_id(hosted_zone)
        environment_A_record = self.get_dns_record(hosted_zone_id=hosted_zone_id, record_name=domain, record_type="A")
        return environment_A_record
