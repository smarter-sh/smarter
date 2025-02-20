"""AWS Route53 helper class."""

# python stuff
import logging
import time
from typing import Tuple

import dns.resolver

from .aws import AWSBase
from .exceptions import AWSRoute53RecordVerificationTimeout


logger = logging.getLogger(__name__)


class AWSHostedZoneNotFound(Exception):
    """Raised when the hosted zone is not found."""


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
        logger.info("%s.get_hosted_zone() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
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
        logger.info("%s.get_or_create_hosted_zone() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
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

    def get_hosted_zone_id(self, hosted_zone) -> str:
        """Return the hosted zone id."""
        logger.info("%s.get_hosted_zone_id() hosted_zone: %s", self.formatted_class_name, hosted_zone)
        if hosted_zone:
            return hosted_zone["Id"].split("/")[-1]
        return None

    def get_hosted_zone_id_for_domain(self, domain_name) -> str:
        """Return the hosted zone id for the domain."""
        logger.info("%s.get_hosted_zone_id_for_domain() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name)
        return self.get_hosted_zone_id(hosted_zone)

    def delete_hosted_zone(self, domain_name):
        # Get the hosted zone id
        logger.info("%s.delete_hosted_zone() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
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
        prefix = self.formatted_class_name + ".get_dns_record()"
        logger.info(
            "%s hosted_zone_id: %s record_name: %s record_type: %s",
            prefix,
            hosted_zone_id,
            record_name,
            record_type,
        )
        record_name = self.domain_resolver(record_name)

        def name_match(record_name, record) -> bool:
            return record["Name"] == record_name or record["Name"] == f"{record_name}."

        paginator = self.client.get_paginator("list_resource_record_sets")
        for page in paginator.paginate(HostedZoneId=hosted_zone_id):
            for record in page["ResourceRecordSets"]:
                if (
                    name_match(record_name=record_name, record=record)
                    and str(record["Type"]).upper() == record_type.upper()
                ):
                    logger.info("%s found record: %s", prefix, record)
                    return record
        logger.warning("%s did not find record for %s %s", prefix, record_name, record_type)
        return None

    def get_ns_records(self, hosted_zone_id: str):
        """
        Return the NS records from the hosted zone.
        example return value:
        [
            {
                "Name": "example.com.",
                "Type": "NS",
                "TTL": 600,
                "ResourceRecords": [
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
            },
        ]
        """
        logger.info("%s.get_ns_records() hosted_zone_id: %s", self.formatted_class_name, hosted_zone_id)
        response = self.client.list_resource_record_sets(HostedZoneId=hosted_zone_id)
        retval = []
        for record in response["ResourceRecordSets"]:
            if record["Type"] == "NS":
                retval.append(record)
        return retval

    # pylint: disable=too-many-arguments,too-many-locals
    def get_or_create_dns_record(
        self,
        hosted_zone_id: str,
        record_name: str,
        record_type: str,
        record_ttl: int,
        record_alias_target: dict = None,
        record_value=None,  # can be a single text value of a list of dict
    ) -> Tuple[dict, bool]:
        action: str = None
        fn_name = self.formatted_class_name + "get_or_create_dns_record()"
        logger.info(
            "%s hosted_zone_id: %s record_name: %s record_type: %s",
            fn_name,
            hosted_zone_id,
            record_name,
            record_type,
        )

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
                return (fetched_record, False)
            action = "UPSERT"
            logger.info("%s updating %s %s record", fn_name, record_name, record_type)
        else:
            action = "CREATE"
            logger.info("%s creating %s %s record", fn_name, record_name, record_type)

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
        logger.info("%s posted aws route53 change batch %s", fn_name, change_batch)

        record = None
        attempts = 0
        max_attempts = 10
        sleep_time = 15
        while not record:
            record = self.get_dns_record(
                hosted_zone_id=hosted_zone_id, record_name=record_name, record_type=record_type
            )
            if record:
                break
            logger.info(
                "%s waiting %s seconds for record to be created. Attempt %s of %s",
                fn_name,
                sleep_time,
                attempts,
                max_attempts,
            )
            time.sleep(sleep_time)
            attempts += 1
            if attempts >= max_attempts:
                raise AWSRoute53RecordVerificationTimeout(
                    f"DNS record verification timeout. Waited unsuccessfully for {attempts * sleep_time} seconds for record {record_name} {record_type} to be created."
                )
        return (record, action == "CREATE")

    def destroy_dns_record(
        self,
        hosted_zone_id: str,
        record_name: str,
        record_type: str,
        record_ttl: int,
        alias_target=None,  # may or may not exist
        record_resource_records=None,  # can be a single text value of a list of dict
    ) -> None:
        """Destroy the DNS record."""
        logger.info(
            "%s.destroy_dns_record() hosted_zone_id: %s record_name: %s record_type: %s",
            self.formatted_class_name,
            hosted_zone_id,
            record_name,
            record_type,
        )
        change_batch = {
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": record_type,
                    },
                },
            ]
        }
        if alias_target:
            change_batch["Changes"][0]["ResourceRecordSet"]["AliasTarget"] = alias_target
        if record_resource_records:
            change_batch["Changes"][0]["ResourceRecordSet"]["TTL"] = record_ttl
            if isinstance(record_resource_records, list):
                change_batch["Changes"][0]["ResourceRecordSet"]["ResourceRecords"] = [
                    {"Value": item["Value"]} for item in record_resource_records if "Value" in item
                ]
            else:
                change_batch["Changes"][0]["ResourceRecordSet"]["ResourceRecords"] = [
                    {"Value": f'"{record_resource_records}"'}
                ]

        print("change_batch", change_batch)
        self.client.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=change_batch,
        )

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
        logger.info("%s.get_environment_A_record() domain: %s", self.formatted_class_name, domain)
        domain = domain or self.environment_domain
        domain = self.domain_resolver(domain)
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name=domain)
        hosted_zone_id = self.get_hosted_zone_id(hosted_zone)
        environment_A_record = self.get_dns_record(hosted_zone_id=hosted_zone_id, record_name=domain, record_type="A")
        return environment_A_record

    def verify_dns_record(self, domain_name: str) -> bool:
        """Verify the DNS record."""
        prefix = self.formatted_class_name + ".verify_dns_record()"
        logger.info("%s - %s", prefix, domain_name)
        domain_name = self.domain_resolver(domain_name)

        for _ in range(15):
            try:
                answers = dns.resolver.resolve(domain_name, "A")
                if len(answers) > 0:
                    logger.info("Domain %s is verified.", domain_name)
                    return True
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                logger.info("%s did not find domain %s. Sleeping 60 seconds", prefix, domain_name)
                time.sleep(60)
        logger.error("Domain %s does not exist or no DNS answer after multiple attempts", domain_name)
        return False
