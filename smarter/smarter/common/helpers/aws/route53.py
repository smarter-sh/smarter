"""AWS Route53 helper class."""

# python stuff
import logging
import time
from typing import Optional, Tuple

import botocore
import botocore.exceptions
import dns.resolver
from django.conf import settings

from smarter.common.helpers.console_helpers import formatted_text

from .aws import AWSBase, SmarterAWSException
from .exceptions import AWSRoute53RecordVerificationTimeout


logger = logging.getLogger(__name__)
module_prefix = "smarter.common.helpers.aws.route53."


class AWSHostedZoneNotFound(Exception):
    """Raised when the hosted zone is not found."""


class AWSRoute53(AWSBase):
    """
    Provides a comprehensive, high-level interface for managing AWS Route53 resources within the application.

    This helper class abstracts the complexities of interacting directly with the AWS Route53 API, offering
    a set of convenient methods for common DNS management tasks such as creating, retrieving, updating, and
    deleting hosted zones and DNS records. By encapsulating these operations, the class enables developers
    to manage DNS infrastructure programmatically in a consistent and reliable manner.

    The class is designed to be used as part of a broader AWS infrastructure management system, leveraging
    the application's AWS session and configuration. It ensures that all Route53 operations are performed
    using the correct credentials and region, as determined by the application's environment and settings.

    Key features include:

    - **Lazy Initialization:** The underlying boto3 Route53 client is instantiated only when first needed,
      reducing unnecessary resource usage and startup time.
    - **Hosted Zone Management:** Methods are provided to retrieve existing hosted zones, create new ones
      if necessary, and delete hosted zones along with their associated records. This simplifies the
      lifecycle management of DNS zones for dynamic environments.
    - **DNS Record Operations:** The class supports creating, updating, retrieving, and deleting DNS records
      (such as A and NS records) within a hosted zone. It handles the nuances of AWS Route53's API, including
      batching changes and waiting for DNS propagation.
    - **Domain Verification:** Utilities are included to verify DNS record propagation, accounting for the
      variable delays inherent in global DNS systems.
    - **Error Handling:** Custom exceptions are raised for common failure scenarios, such as missing hosted
      zones or DNS records, making it easier to diagnose and handle errors in higher-level application logic.
    - **Integration with Application Settings:** The class uses application-level settings (such as default TTL)
      and logging, ensuring that DNS operations are traceable and configurable.

    By using this class, developers can automate DNS management tasks as part of deployment, scaling, or
    teardown workflows, reducing manual intervention and the risk of configuration drift. The class is
    intended to be subclassed or instantiated as part of a larger AWS infrastructure management toolkit,
    and is suitable for both production and testing environments.

    Example use cases include:

    - Automatically provisioning DNS records for new application environments or tenants.
    - Verifying that DNS changes have propagated before proceeding with dependent operations.
    - Cleaning up DNS resources as part of environment teardown or migration processes.

    This design promotes maintainability, reliability, and clarity in DNS management, making Route53
    operations accessible and robust for all parts of the application.
    """

    _client = None

    @property
    def client(self):
        """
        Return the AWS Route53 client.

        :return: Boto3 Route53 client.
        :rtype: botocore.client.Route53
        """
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("route53")
        return self._client

    def get_hosted_zone(self, domain_name) -> Optional[str]:
        """
        Return the hosted zone.

        :return: Hosted zone dictionary or None if not found.
        :rtype: Optional[dict]
        """
        logger.info("%s.get_hosted_zone() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
        response = self.client.list_hosted_zones()
        for hosted_zone in response["HostedZones"]:
            if hosted_zone["Name"] == domain_name or hosted_zone["Name"] == f"{domain_name}.":
                return hosted_zone
        return None

    def get_or_create_hosted_zone(self, domain_name) -> tuple[dict, bool]:
        """
        Retrieve an existing hosted zone for the given domain, or create one if it does not exist.

        This method checks if a Route53 hosted zone exists for the specified domain name. If the hosted zone
        is found, it is returned along with a boolean flag indicating that it was not newly created. If the
        hosted zone does not exist, the method creates a new public hosted zone for the domain, waits for
        its creation, and then returns the new hosted zone along with a boolean flag indicating creation.

        The returned dictionary contains details about the hosted zone and its delegation set, including
        the hosted zone ID, name, configuration, and the list of authoritative name servers.

        Example return value:

        .. code-block:: json

                    {
                    "HostedZone": {
                        "Id": "/hostedzone/Z148QEXAMPLE8V",
                        "Name": "example.com.",
                        "CallerReference": "my hosted zone",
                        "Config": {
                            "Comment": "This is my hosted zone",
                            "PrivateZone": false
                        },
                        "ResourceRecordSetCount": 2
                    },
                    "DelegationSet": {
                        "NameServers": [
                            "ns-2048.awsdns-64.com",
                            "ns-2049.awsdns-65.net",
                            "ns-2050.awsdns-66.org",
                            "ns-2051.awsdns-67.co.uk"
                        ]
                    }
                }

        :param domain_name: The domain name for which to retrieve or create the hosted zone.
        :type domain_name: str
        :return: A tuple containing the hosted zone dictionary and a boolean indicating if it was created.
        :rtype: Tuple[dict, bool]
        :raises AWSHostedZoneNotFound: If the hosted zone could not be found or created.
        """
        logger.info("%s.get_or_create_hosted_zone() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
        hosted_zone = self.get_hosted_zone(domain_name)
        if isinstance(hosted_zone, dict):
            return (hosted_zone, False)

        self.client.create_hosted_zone(
            Name=domain_name,
            CallerReference=str(time.time()),  # Unique string used to identify the request
            HostedZoneConfig={"Comment": "Managed by Smarter manage.py verify_dns_configuration", "PrivateZone": False},
        )
        hosted_zone = self.get_hosted_zone(domain_name)
        if not isinstance(hosted_zone, dict):
            raise AWSHostedZoneNotFound(f"Hosted zone not found for domain {domain_name}")
        logger.info("Created hosted zone %s %s", hosted_zone, domain_name)
        return (hosted_zone, True)

    def get_hosted_zone_id(self, hosted_zone) -> str:
        """
        Return the hosted zone id.

        :param hosted_zone: The hosted zone dictionary.
        :type hosted_zone: dict
        :return: The hosted zone ID.
        :rtype: str
        :raises AWSHostedZoneNotFound: If the hosted zone ID could not be found.
        """
        logger.info("%s.get_hosted_zone_id() hosted_zone: %s", self.formatted_class_name, hosted_zone)
        if isinstance(hosted_zone, dict) and "Id" in hosted_zone:
            return hosted_zone["Id"].split("/")[-1]
        else:
            raise AWSHostedZoneNotFound(f"Hosted zone not found for {hosted_zone}. Expected a dict with 'Id' key.")

    def get_hosted_zone_by_id(self, hosted_zone_id) -> Optional[dict]:
        """
        (NOT IMPLEMENTED) Return the AWS Route53 Hosted zone for the zone id

        :param hosted_zone_id: The hosted zone ID.
        :type hosted_zone_id: str
        :return: Hosted zone dictionary or None if not found.
        :rtype: Optional[dict]

        .. todo:: implement this method
        """

    def get_hosted_zone_id_for_domain(self, domain_name) -> str:
        """
        Return the hosted zone id for the domain.

        :param domain_name: The domain name.
        :type domain_name: str
        :return: The hosted zone ID.
        :rtype: str
        """
        logger.info("%s.get_hosted_zone_id_for_domain() domain_name: %s", self.formatted_class_name, domain_name)
        domain_name = self.domain_resolver(domain_name)
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name)
        return self.get_hosted_zone_id(hosted_zone)

    def get_ns_records_for_domain(self, domain: str) -> dict:
        """
        Retrieve the NS (Name Server) records for a hosted zone associated with the given domain.

        This helper method locates the hosted zone for the specified domain and returns the NS record set,
        which contains the authoritative name servers for the domain. The returned dictionary includes the
        record name, type, TTL, and a list of name server values.

        Example return value:

        .. code-block:: json

            {
                "Name": "example.com.",
                "Type": "NS",
                "TTL": 600,
                "ResourceRecords": [
                    {"Value": "ns-2048.awsdns-64.com"},
                    {"Value": "ns-2049.awsdns-65.net"},
                    {"Value": "ns-2050.awsdns-66.org"},
                    {"Value": "ns-2051.awsdns-67.co.uk"}
                ]
            }

        :param domain: The domain name for which to retrieve NS records.
        :type domain: str
        :return: A dictionary representing the NS record set for the domain.
        :rtype: dict
        :raises AWSHostedZoneNotFound: If NS records cannot be found for the domain.
        """
        domain = self.domain_resolver(domain)
        hosted_zone_id = self.get_hosted_zone_id_for_domain(domain_name=domain)
        ns_records = self.get_ns_records(hosted_zone_id=hosted_zone_id)
        # noting that a hosted zone can have multiple NS records, we need to find
        # the NS records for the domain of the hosted zone itself.
        if isinstance(ns_records, list) and len(ns_records) > 0:
            # return the first NS record that matches the domain name
            # or the domain name with a trailing dot
            logger.info(
                "%s.get_ns_records_for_domain() found %s NS records", self.formatted_class_name, len(ns_records)
            )
            return next(item for item in ns_records if item["Name"] in [domain, f"{domain}."])
        raise AWSHostedZoneNotFound(
            f"NS records not found for domain {domain}. Make sure the domain is registered and the hosted zone exists."
        )

    def delete_hosted_zone(self, domain_name):
        """
        Delete the hosted zone and all its record sets.

        :param domain_name: The domain name of the hosted zone to delete.
        :type domain_name: str
        :return: None
        :rtype: None
        """
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

    def get_dns_record(self, hosted_zone_id: str, record_name: str, record_type: str) -> Optional[dict]:
        """
        Return the DNS record from the hosted zone.

        This method retrieves a specific DNS record from the given hosted zone, matching both the record name and type.
        It searches through all resource record sets in the hosted zone and returns the first record that matches
        the provided name and type. If no matching record is found, the method returns None.

        Example return value:

        .. code-block:: json

            {
                "Name": "example.com.",
                "Type": "A",
                "TTL": 300,
                "ResourceRecords": [
                    {"Value": "192.1.1.1"}
                ]
            }

        :param hosted_zone_id: The ID of the hosted zone to search.
        :type hosted_zone_id: str
        :param record_name: The DNS record name to look for.
        :type record_name: str
        :param record_type: The DNS record type (e.g., "A", "CNAME", "NS").
        :type record_type: str
        :return: The DNS record dictionary if found, otherwise None.
        :rtype: Optional[dict]
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
        Return the NS (Name Server) records from the hosted zone.

        This method retrieves all NS records associated with the specified hosted zone. The returned value is a list
        of dictionaries, each representing an NS record set, including the record name, type, TTL, and the list of
        authoritative name servers.

        Example return value:

        .. code-block:: json

            [
                {
                    "Name": "example.com.",
                    "Type": "NS",
                    "TTL": 600,
                    "ResourceRecords": [
                        {"Value": "ns-2048.awsdns-64.com"},
                        {"Value": "ns-2049.awsdns-65.net"},
                        {"Value": "ns-2050.awsdns-66.org"},
                        {"Value": "ns-2051.awsdns-67.co.uk"}
                    ]
                }
            ]

        :param hosted_zone_id: The ID of the hosted zone from which to retrieve NS records.
        :type hosted_zone_id: str
        :return: A list of dictionaries representing the NS record sets for the hosted zone.
        :rtype: list
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
        record_alias_target: Optional[dict] = None,
        record_value=None,  # can be a single text value of a list of dict
    ) -> Tuple[dict, bool]:
        """
        Get or create the DNS record in the hosted zone.

        This method attempts to retrieve a DNS record from the specified hosted zone. If the record exists and
        matches the provided values or alias target, it is returned along with a flag indicating that it was not created.
        If the record does not exist or does not match, the method creates or updates the record accordingly.
        The method waits for the record to be created or updated before returning.

        :param hosted_zone_id: The ID of the hosted zone.
        :type hosted_zone_id: str
        :param record_name: The DNS record name.
        :type record_name: str
        :param record_type: The DNS record type (e.g., "A", "CNAME", "NS").
        :type record_type: str
        :param record_ttl: The TTL (Time to Live) for the DNS record.
        :type record_ttl: int
        :param record_alias_target: The alias target for the DNS record, if applicable.
        :type record_alias_target: Optional[dict]
        :param record_value: The value(s) for the DNS record, which can be a single text value or a list of dictionaries.
        :type record_value: Union[str, List[dict], None]
        :return: A tuple containing the DNS record dictionary and a boolean indicating whether the record was created (True) or already existed (False).
        :rtype: Tuple[dict, bool]

        """
        action: Optional[str] = None
        fn_name = self.formatted_class_name + ".get_or_create_dns_record()"
        logger.info(
            "%s hosted_zone_id: %s record_name: %s record_type: %s record_ttl: %s record_alias_target: %s record_value: %s",
            fn_name,
            hosted_zone_id,
            record_name,
            record_type,
            record_ttl,
            record_alias_target,
            record_value,
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
                logger.info("%s returning matched record: %s", fn_name, fetched_record)
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

        try:
            self.client.change_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                ChangeBatch=change_batch,
            )
            logger.info("%s posted aws route53 change batch %s", fn_name, change_batch)
        except Exception as e:
            msg = f"{fn_name} failed to post aws route53 change batch in hosted zone {hosted_zone_id}\n{change_batch}:\n{e}"
            logger.error(msg)
            raise SmarterAWSException(msg) from e

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
        record_type: str = "A",
        record_ttl: int = 600,
        alias_target=None,  # may or may not exist
        record_resource_records=None,  # can be a single text value of a list of dict
    ) -> None:
        """
        Destroy the DNS record.

        :param hosted_zone_id: The ID of the hosted zone.
        :type hosted_zone_id: str
        :param record_name: The DNS record name.
        :type record_name: str
        :param record_type: The DNS record type (e.g., "A", "CNAME", "NS").
        :type record_type: str
        :param record_ttl: The TTL (Time to Live) for the DNS record.
        :type record_ttl: int
        :param alias_target: The alias target for the DNS record, if applicable.
        :type alias_target: Optional[dict]
        :param record_resource_records: The value(s) for the DNS record, which can be a single text value or a list of dictionaries.
        :type record_resource_records: Union[str, List[dict], None]
        :return: None
        :rtype: None
        """
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
            record_ttl = record_ttl or change_batch["Changes"][0]["ResourceRecordSet"]["TTL"]
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

    def get_environment_A_record(self, domain: Optional[str] = None) -> Optional[dict]:
        """
        Return the DNS A record for the environment domain.

        This method retrieves the DNS A record associated with the environment's domain. If no domain is provided,
        it uses the default environment domain configured for the application. The returned dictionary contains
        details about the A record, including the record name, type, TTL, and the list of IP address values.

        Example return value:

        .. code-block:: json

            {
                "Name": "example.com.",
                "Type": "A",
                "TTL": 300,
                "ResourceRecords": [{"Value": "192.1.1.1"}]
            }

        :param domain: The domain name for which to retrieve the A record. If None, uses the environment domain.
        :type domain: Optional[str]
        :return: The DNS A record dictionary if found, otherwise None.
        :rtype: Optional[dict]
        """
        logger.info("%s.get_environment_A_record() domain: %s", self.formatted_class_name, domain)
        domain = domain or self.environment_domain
        domain = self.domain_resolver(domain)
        hosted_zone, _ = self.get_or_create_hosted_zone(domain_name=domain)
        hosted_zone_id = self.get_hosted_zone_id(hosted_zone)
        environment_A_record = self.get_dns_record(hosted_zone_id=hosted_zone_id, record_name=domain, record_type="A")
        return environment_A_record

    def verify_dns_record(self, domain_name: str) -> bool:
        """
        Verify the DNS record for the given domain name.

        DNS propagation can take a variable amount of time depending on the DNS provider and geographic location.
        For example, in some regions it may take up to an hour for AWS Route53 records to propagate, while within
        an AWS VPC it typically takes less than 5 minutes. This method attempts to resolve the domain's A record
        every 60 seconds for up to 15 minutes, allowing for DNS propagation delays.

        Note that other Kubernetes functions or AWS services that depend on DNS records may be able to see
        the records before they are visible from your current location.

        :param domain_name: The domain name to verify.
        :type domain_name: str
        :return: True if the DNS A record is found within the timeout period, otherwise False.
        :rtype: bool
        """
        prefix = self.formatted_class_name + ".verify_dns_record()"
        logger.info("%s - %s", prefix, domain_name)
        domain_name = self.domain_resolver(domain_name)

        for _ in range(15):
            try:
                answers = dns.resolver.resolve(domain_name, "A")
                if len(answers) > 0:
                    logger.info("%s domain %s is verified.", prefix, domain_name)
                    return True
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                logger.info("%s did not find domain %s. Sleeping 60 seconds", prefix, domain_name)
                time.sleep(60)
        logger.error("Domain %s does not exist or no DNS answer after multiple attempts", domain_name)
        return False

    def create_domain_a_record(self, hostname: str, api_host_domain: str) -> dict:  # type: ignore[no-untyped-def]
        """
        Creates an A record inside an AWS Route53 hosted zone.

        :param hostname: The full hostname for the A record to create (e.g., "api.example.com").
        :type hostname: str
        :param api_host_domain: The parent domain where the hosted zone exists (e.g., "example.com").
        :type api_host_domain: str
        :return: The created DNS record dictionary.
        :rtype: dict
        :raises AWSHostedZoneNotFound: If the hosted zone or deployment record cannot be found
        """
        fn_name = formatted_text(module_prefix + "create_domain_a_record()")
        logger.info("%s for hostname %s, api_host_domain %s", fn_name, hostname, api_host_domain)

        try:
            hostname = self.domain_resolver(hostname)
            api_host_domain = self.domain_resolver(api_host_domain)

            logger.info("%s resolved hostname: %s", fn_name, hostname)

            # add the A record to the customer API domain
            hosted_zone_id = self.get_hosted_zone_id_for_domain(domain_name=api_host_domain)
            logger.info("%s found hosted zone %s for parent domain %s", fn_name, hosted_zone_id, api_host_domain)

            # retrieve the A record from the environment domain hosted zone. we'll
            # use this to create the A record in the customer API domain
            a_record = self.get_environment_A_record(domain=api_host_domain)
            if not a_record:
                raise AWSHostedZoneNotFound(f"Hosted zone not found for domain {api_host_domain}")

            logger.info(
                "%s propagating A record %s from parent domain %s to deployment target %s",
                fn_name,
                a_record,
                api_host_domain,
                hostname,
            )

            deployment_record, created = self.get_or_create_dns_record(
                hosted_zone_id=hosted_zone_id,
                record_name=hostname,
                record_type="A",
                record_alias_target=a_record["AliasTarget"] if "AliasTarget" in a_record else None,
                record_value=a_record["ResourceRecords"] if "ResourceRecords" in a_record else None,
                record_ttl=settings.SMARTER_CHATBOT_TASKS_DEFAULT_TTL,
            )
            verb = "Created" if created else "Verified"
            logger.info(
                "%s %s deployment DNS record %s AWS Route53 hosted zone %s %s",
                fn_name,
                verb,
                deployment_record,
                api_host_domain,
                hosted_zone_id,
            )
            if not isinstance(deployment_record, dict):
                raise AWSHostedZoneNotFound(
                    f"Deployment record not found for {hostname} in hosted zone {hosted_zone_id}"
                )
            return deployment_record

        except botocore.exceptions.ClientError as e:
            # If the domain already exists, we can ignore the error
            if "InvalidChangeBatch" not in str(e):
                raise
