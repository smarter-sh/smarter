"""
Test the AWS helpers, :mod:`smarter.common.helpers.aws`, with fake boto3 clients.

None of these tests reach AWS: every helper's client is a fake, its identity is
set, and boto3.Session is patched, so that a test that forgot to set a client
fails instead of using the container's live AWS credentials.
"""

from unittest.mock import MagicMock, PropertyMock, patch

import boto3
import botocore.exceptions
import dns.resolver

from smarter.common.conf import smarter_settings
from smarter.common.helpers.aws.acm import AWSCertificateManager
from smarter.common.helpers.aws.api_gateway import AWSAPIGateway
from smarter.common.helpers.aws.aws import AWSBase, SmarterAWSException
from smarter.common.helpers.aws.dynamodb import AWSDynamoDB
from smarter.common.helpers.aws.eks import AWSEks
from smarter.common.helpers.aws.exceptions import (
    AWSNotReadyError,
    AWSRoute53RecordVerificationTimeout,
)
from smarter.common.helpers.aws.iam import AWSIdentifyAccessManagement
from smarter.common.helpers.aws.lambda_function import AWSLambdaFunction
from smarter.common.helpers.aws.rds import AWSRds
from smarter.common.helpers.aws.rekognition import AWSRekognition
from smarter.common.helpers.aws.route53 import AWSHostedZoneNotFound, AWSRoute53
from smarter.common.helpers.aws.s3 import AWSSimpleStorageSystem
from smarter.lib.django.validators import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

IDENTITY = {"UserId": "AIDATEST", "Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"}
DOMAIN = "smarter.example.com"
SRI = smarter_settings.shared_resource_identifier


class NotFoundException(Exception):
    """A fake boto3 client's NotFoundException / ResourceNotFoundException."""


class FakeRoute53Client:
    """An in-memory Route53 client: hosted zones and their record sets."""

    def __init__(self):
        self.zones: list[dict] = []
        self.records: dict[str, list[dict]] = {}
        self.changes: list[dict] = []
        self.deleted_zones: list[str] = []

    def add_zone(self, name: str) -> str:
        zone_id = f"Z{len(self.zones) + 1}"
        self.zones.append({"Id": f"/hostedzone/{zone_id}", "Name": f"{name}."})
        self.records[zone_id] = [
            {"Name": f"{name}.", "Type": "NS", "ResourceRecords": [{"Value": "ns-1.awsdns.com."}]},
            {"Name": f"{name}.", "Type": "SOA", "ResourceRecords": [{"Value": "soa"}]},
        ]
        return zone_id

    def list_hosted_zones(self):
        return {"HostedZones": list(self.zones)}

    def create_hosted_zone(self, Name, CallerReference, HostedZoneConfig):  # pylint: disable=invalid-name
        self.add_zone(Name)

    def delete_hosted_zone(self, Id):  # pylint: disable=invalid-name
        self.deleted_zones.append(Id)

    def list_resource_record_sets(self, HostedZoneId):  # pylint: disable=invalid-name
        return {"ResourceRecordSets": list(self.records[HostedZoneId])}

    def get_paginator(self, name):
        paginator = MagicMock()
        paginator.paginate.side_effect = lambda HostedZoneId: [self.list_resource_record_sets(HostedZoneId)]
        return paginator

    def change_resource_record_sets(self, HostedZoneId, ChangeBatch):  # pylint: disable=invalid-name
        self.changes.append(ChangeBatch)
        for change in ChangeBatch["Changes"]:
            record = dict(change["ResourceRecordSet"])
            records = self.records.setdefault(HostedZoneId, [])
            matches = [
                r
                for r in records
                if r["Name"].rstrip(".") == record["Name"].rstrip(".") and r["Type"] == record["Type"]
            ]
            for match in matches:
                records.remove(match)
            if change["Action"] in ("CREATE", "UPSERT"):
                records.append(record)


def connect(helper: AWSBase, client) -> AWSBase:
    """Give a helper a fake client and identity, so that it is ready without AWS."""
    helper._client = client  # pylint: disable=protected-access
    helper._identity = dict(IDENTITY)  # pylint: disable=protected-access
    return helper


class AWSTestBase(SmarterTestBase):
    """Patch boto3.Session, so that no test can create a real AWS client."""

    def setUp(self):
        super().setUp()
        self.session_patcher = patch("smarter.common.helpers.aws.aws.boto3.Session")
        self.mock_session = self.session_patcher.start()
        self.addCleanup(self.session_patcher.stop)

    def unpatch_session(self):
        """Restore boto3.Session, for a test of the helper's isinstance(session, boto3.Session) check.

        The test must set the helper's session itself, so that it never creates one.
        """
        self.session_patcher.stop()


class TestAWSBase(AWSTestBase):
    """Test the AWSBase's authentication, session, identity and domain helpers."""

    def test_properties(self):
        helper = AWSBase(shared_resource_identifier="sri", environment="alpha", root_domain="example.com")
        self.assertEqual(helper.shared_resource_identifier, "sri")
        self.assertEqual(helper.environment, "alpha")
        self.assertEqual(helper.root_domain, "example.com")
        self.assertEqual(helper.environment_api_domain, "alpha.api.example.com")
        self.assertEqual(helper.environment_domain, smarter_settings.environment_platform_domain)
        self.assertIsInstance(helper.version, str)
        self.assertIsInstance(helper.debug_mode, bool)
        self.assertEqual(helper.aws_is_configured, smarter_settings.aws_is_configured)
        self.assertEqual(
            set(helper.aws_auth.keys()),
            {"aws_profile", "aws_access_key_id_source", "aws_secret_access_key_source", "aws_region"},
        )
        self.assertIsInstance(helper.authentication_credentials_state, str)

    def test_init_with_keys(self):
        helper = AWSBase(
            aws_access_key_id="id", aws_secret_access_key="secret", aws_region="us-east-1", aws_profile=None
        )
        self.assertEqual(helper.aws_region, "us-east-1")
        if helper.aws_profile is None and helper.aws_access_key_id:
            self.assertEqual(helper.aws_access_key_id_source, "passed parameter")
            self.assertEqual(helper.aws_secret_access_key_source, "passed parameter")
            self.assertTrue(helper.authentication_credentials_are_initialized)

    def test_init_with_profile(self):
        helper = AWSBase(aws_profile="a-profile")
        self.assertEqual(helper.aws_profile, "a-profile")
        self.assertEqual(helper.aws_access_key_id_source, "aws_profile")
        self.assertTrue(helper.authentication_credentials_are_initialized)

    def test_init_aws_deployed(self):
        with patch.dict("os.environ", {"AWS_DEPLOYED": "true"}):
            helper = AWSBase()
            self.assertTrue(helper.is_aws_deployed)
        self.assertEqual(helper.aws_access_key_id_source, "overridden by IAM role-based security")

    def test_session_with_profile(self):
        helper = AWSBase(aws_profile="a-profile", aws_region="us-east-1")
        self.assertIs(helper.aws_session, self.mock_session.return_value)
        self.mock_session.assert_any_call(profile_name="a-profile", region_name="us-east-1")
        # the session is cached.
        calls = self.mock_session.call_count
        self.assertIs(helper.aws_session, self.mock_session.return_value)
        self.assertEqual(self.mock_session.call_count, calls)

    def test_session_with_missing_profile_falls_back(self):
        """Test that a missing profile falls back to the key pair, and then to a session without credentials."""
        sessions = [botocore.exceptions.ProfileNotFound(profile="a-profile"), Exception("bad keys"), "session"]
        self.mock_session.side_effect = sessions
        helper = AWSBase(aws_profile="a-profile", aws_region="us-east-1")
        helper._aws_access_key_id = "id"  # pylint: disable=protected-access
        helper._aws_secret_access_key = "secret"  # pylint: disable=protected-access
        self.assertEqual(helper.aws_session, "session")
        self.assertEqual(self.mock_session.call_count, 3)

    def test_session_with_keys(self):
        helper = AWSBase(aws_access_key_id="id", aws_secret_access_key="secret", aws_region="us-east-1")
        helper._aws_profile = None  # pylint: disable=protected-access
        helper._authentication_credentials_are_initialized = True  # pylint: disable=protected-access
        helper._aws_access_key_id, helper._aws_secret_access_key = "id", "secret"  # pylint: disable=protected-access
        self.assertIs(helper.aws_session, self.mock_session.return_value)
        self.mock_session.assert_any_call(
            region_name="us-east-1", aws_access_key_id="id", aws_secret_access_key="secret"
        )

    def test_session_without_credentials_fails(self):
        self.mock_session.side_effect = Exception("no credentials")
        helper = AWSBase(aws_region="us-east-1")
        helper._aws_profile = None  # pylint: disable=protected-access
        helper._aws_access_key_id = helper._aws_secret_access_key = None  # pylint: disable=protected-access
        helper._authentication_credentials_are_initialized = True  # pylint: disable=protected-access
        self.assertIsNone(helper.aws_session)

    def test_not_initialized(self):
        """Test that a helper without credentials has no session, identity, account or client."""
        helper = AWSBase()
        helper._authentication_credentials_are_initialized = False  # pylint: disable=protected-access
        self.assertIsNone(helper.aws_session)
        self.assertIsNone(helper.identity)
        self.assertFalse(helper.ready)
        self.assertIsNone(helper.aws_account_id)
        self.assertIsNone(helper.aws_iam_arn)

    def test_identity(self):
        helper = AWSBase(aws_profile="a-profile")
        self.mock_session.return_value.client.return_value.get_caller_identity.return_value = dict(IDENTITY)
        self.assertEqual(helper.identity, IDENTITY)
        self.assertTrue(helper.ready)
        self.assertEqual(helper.aws_account_id, IDENTITY["Account"])
        self.assertEqual(helper.aws_iam_arn, IDENTITY["Arn"])
        self.mock_session.return_value.client.assert_called_with("sts")

    def test_identity_error(self):
        helper = AWSBase(aws_profile="a-profile")
        self.mock_session.return_value.client.return_value.get_caller_identity.side_effect = Exception("denied")
        self.assertIsNone(helper.identity)
        self.assertFalse(helper.ready)

    def test_client(self):
        helper = AWSBase(aws_profile="a-profile")
        with self.assertRaises(SmarterAWSException):
            _ = helper.client  # no client type
        helper._client_type = "s3"  # pylint: disable=protected-access
        self.mock_session.return_value.client.return_value.get_caller_identity.return_value = None
        self.assertIsNone(helper.client)  # not ready
        helper._identity = dict(IDENTITY)  # pylint: disable=protected-access
        helper._aws_session = MagicMock()  # pylint: disable=protected-access
        self.unpatch_session()
        self.assertIsNone(helper.client)  # the session is not a boto3.Session

    def test_client_created(self):
        helper = AWSBase(aws_profile="a-profile")
        helper._client_type = "s3"  # pylint: disable=protected-access
        helper._identity = dict(IDENTITY)  # pylint: disable=protected-access
        self.unpatch_session()
        session = MagicMock(spec=boto3.Session)
        helper._aws_session = session  # pylint: disable=protected-access
        self.assertIs(helper.client, session.client.return_value)
        session.client.assert_called_once_with("s3")
        self.assertIs(helper.client, session.client.return_value)  # cached

    def test_client_error(self):
        helper = AWSBase(aws_profile="a-profile")
        helper._client_type = "s3"  # pylint: disable=protected-access
        helper._identity = dict(IDENTITY)  # pylint: disable=protected-access
        self.unpatch_session()
        session = MagicMock(spec=boto3.Session)
        session.client.side_effect = botocore.exceptions.BotoCoreError()
        helper._aws_session = session  # pylint: disable=protected-access
        self.assertIsNone(helper.client)

    def test_domain_resolver(self):
        helper = AWSBase(environment="alpha")
        self.assertEqual(helper.domain_resolver(DOMAIN), DOMAIN)
        with self.assertRaises(SmarterValueError):
            helper.domain_resolver("localhost")

    def test_domain_resolver_local_proxy(self):
        """Test that a local environment's platform and api domains are replaced with their proxy domains."""
        helper = AWSBase(environment="local", root_domain="example.com")
        domain = f"bot.{smarter_settings.environment_api_domain}"
        self.assertEqual(helper.domain_resolver(domain), f"bot.{helper.environment_api_domain}")


class TestAWSRoute53(AWSTestBase):
    """Test AWSRoute53 with an in-memory Route53 client."""

    def setUp(self):
        super().setUp()
        self.client = FakeRoute53Client()
        self.zone_id = self.client.add_zone(DOMAIN)
        self.route53 = connect(AWSRoute53(), self.client)
        sleep = patch("smarter.common.helpers.aws.route53.time.sleep")
        self.mock_sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def test_get_hosted_zone(self):
        self.assertEqual(self.route53.get_hosted_zone(DOMAIN)["Name"], f"{DOMAIN}.")
        self.assertIsNone(self.route53.get_hosted_zone("other.example.com"))

    def test_get_or_create_hosted_zone(self):
        zone, created = self.route53.get_or_create_hosted_zone(DOMAIN)
        self.assertFalse(created)
        zone, created = self.route53.get_or_create_hosted_zone("new.example.com")
        self.assertTrue(created)
        self.assertEqual(zone["Name"], "new.example.com.")

    def test_get_or_create_hosted_zone_not_found(self):
        self.client.create_hosted_zone = MagicMock()
        with self.assertRaises(AWSHostedZoneNotFound):
            self.route53.get_or_create_hosted_zone("new.example.com")

    def test_hosted_zone_ids(self):
        self.assertEqual(self.route53.get_hosted_zone_id({"Id": "/hostedzone/Z9"}), "Z9")
        with self.assertRaises(AWSHostedZoneNotFound):
            self.route53.get_hosted_zone_id(None)
        self.assertEqual(self.route53.get_hosted_zone_id_for_domain(DOMAIN), self.zone_id)
        with self.assertRaises(NotImplementedError):
            self.route53.get_hosted_zone_by_id(self.zone_id)

    def test_ns_records(self):
        self.assertEqual(len(self.route53.get_ns_records(self.zone_id)), 1)
        self.assertEqual(self.route53.get_ns_records_for_domain(DOMAIN)["Type"], "NS")
        self.client.records[self.zone_id] = []
        with self.assertRaises(AWSHostedZoneNotFound):
            self.route53.get_ns_records_for_domain(DOMAIN)

    def test_delete_hosted_zone(self):
        """Test that a hosted zone's records, other than NS and SOA, are deleted, and then the zone."""
        self.client.records[self.zone_id].append({"Name": f"a.{DOMAIN}.", "Type": "A", "TTL": 60})
        self.route53.delete_hosted_zone(DOMAIN)
        self.assertEqual([r["Type"] for r in self.client.records[self.zone_id]], ["NS", "SOA"])
        self.assertEqual(self.client.deleted_zones, [self.zone_id])

    def test_get_dns_record(self):
        self.assertEqual(self.route53.get_dns_record(self.zone_id, DOMAIN, "ns")["Type"], "NS")
        self.assertIsNone(self.route53.get_dns_record(self.zone_id, DOMAIN, "A"))

    def test_get_or_create_dns_record_value(self):
        """Test that a record is created, then found unchanged, then updated with a new value."""
        name = f"a.{DOMAIN}"
        values = [{"Value": "1.2.3.4"}]
        record, created = self.route53.get_or_create_dns_record(self.zone_id, name, "A", 600, record_value=values)
        self.assertTrue(created)
        self.assertEqual(record["ResourceRecords"], values)
        self.assertEqual(record["TTL"], 600)

        record, created = self.route53.get_or_create_dns_record(self.zone_id, name, "A", 600, record_value=values)
        self.assertFalse(created)
        self.assertEqual(len(self.client.changes), 1)

        record, created = self.route53.get_or_create_dns_record(
            self.zone_id, name, "A", 600, record_value=[{"Value": "5.6.7.8"}]
        )
        self.assertFalse(created)
        self.assertEqual(self.client.changes[-1]["Changes"][0]["Action"], "UPSERT")
        self.assertEqual(record["ResourceRecords"], [{"Value": "5.6.7.8"}])

    def test_get_or_create_dns_record_text_value(self):
        record, created = self.route53.get_or_create_dns_record(
            self.zone_id, f"t.{DOMAIN}", "TXT", 300, record_value="hello"
        )
        self.assertTrue(created)
        self.assertEqual(record["ResourceRecords"], [{"Value": '"hello"'}])

    def test_get_or_create_dns_record_alias(self):
        alias = {"HostedZoneId": "ZELB", "DNSName": "elb.amazonaws.com.", "EvaluateTargetHealth": False}
        record, created = self.route53.get_or_create_dns_record(
            self.zone_id, f"b.{DOMAIN}", "A", 600, record_alias_target=alias
        )
        self.assertTrue(created)
        self.assertEqual(record["AliasTarget"], alias)
        _, created = self.route53.get_or_create_dns_record(
            self.zone_id, f"b.{DOMAIN}", "A", 600, record_alias_target=alias
        )
        self.assertFalse(created)

    def test_get_or_create_dns_record_change_error(self):
        self.client.change_resource_record_sets = MagicMock(side_effect=Exception("InvalidChangeBatch"))
        with self.assertRaises(SmarterAWSException):
            self.route53.get_or_create_dns_record(
                self.zone_id, f"c.{DOMAIN}", "A", 600, record_value=[{"Value": "1.2.3.4"}]
            )

    def test_get_or_create_dns_record_timeout(self):
        """Test that a record that never appears times out, after waiting between attempts."""
        self.client.change_resource_record_sets = MagicMock()
        with self.assertRaises(AWSRoute53RecordVerificationTimeout):
            self.route53.get_or_create_dns_record(
                self.zone_id, f"d.{DOMAIN}", "A", 600, record_value=[{"Value": "1.2.3.4"}]
            )
        self.assertEqual(self.mock_sleep.call_count, 10)

    def test_destroy_dns_record(self):
        name = f"e.{DOMAIN}"
        self.route53.get_or_create_dns_record(self.zone_id, name, "A", 600, record_value=[{"Value": "1.2.3.4"}])
        with patch("builtins.print"):
            self.route53.destroy_dns_record(
                self.zone_id, name, "A", 600, record_resource_records=[{"Value": "1.2.3.4"}]
            )
            self.route53.destroy_dns_record(self.zone_id, name, "TXT", 600, record_resource_records="hello")
            self.route53.destroy_dns_record(self.zone_id, name, "A", alias_target={"DNSName": "elb."})
        self.assertIsNone(self.route53.get_dns_record(self.zone_id, name, "A"))
        self.assertEqual(
            self.client.changes[-2]["Changes"][0]["ResourceRecordSet"]["ResourceRecords"], [{"Value": '"hello"'}]
        )
        self.assertEqual(self.client.changes[-1]["Changes"][0]["ResourceRecordSet"]["AliasTarget"], {"DNSName": "elb."})

    def test_get_environment_A_record(self):  # pylint: disable=invalid-name
        self.assertIsNone(self.route53.get_environment_A_record(DOMAIN))
        self.client.records[self.zone_id].append(
            {"Name": f"{DOMAIN}.", "Type": "A", "ResourceRecords": [{"Value": "1.2.3.4"}]}
        )
        self.assertEqual(self.route53.get_environment_A_record(DOMAIN)["Type"], "A")

    def test_verify_dns_record(self):
        with patch("smarter.common.helpers.aws.route53.dns.resolver.resolve", return_value=["1.2.3.4"]):
            self.assertTrue(self.route53.verify_dns_record(DOMAIN))
        with patch("smarter.common.helpers.aws.route53.dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN):
            self.assertFalse(self.route53.verify_dns_record(DOMAIN))
        self.assertEqual(self.mock_sleep.call_count, 15)

    def test_create_domain_a_record(self):
        """Test that a deployment's A record copies its api domain's A record."""
        self.client.records[self.zone_id].append(
            {"Name": f"{DOMAIN}.", "Type": "A", "ResourceRecords": [{"Value": "1.2.3.4"}]}
        )
        record, created = self.route53.create_domain_a_record(hostname=f"bot.{DOMAIN}", api_host_domain=DOMAIN)
        self.assertTrue(created)
        self.assertEqual(record["ResourceRecords"], [{"Value": "1.2.3.4"}])
        _, created = self.route53.create_domain_a_record(hostname=f"bot.{DOMAIN}", api_host_domain=DOMAIN)
        self.assertFalse(created)

    def test_create_domain_a_record_without_parent(self):
        with self.assertRaises(AWSHostedZoneNotFound):
            self.route53.create_domain_a_record(hostname=f"bot.{DOMAIN}", api_host_domain=DOMAIN)

    def test_create_domain_a_record_client_error(self):
        """Test that an InvalidChangeBatch client error is ignored, and any other is raised."""
        for code, raises in (("InvalidChangeBatch", False), ("AccessDenied", True)):
            error = botocore.exceptions.ClientError(
                {"Error": {"Code": code, "Message": code}}, "ChangeResourceRecordSets"
            )
            with self.subTest(code=code), patch.object(AWSRoute53, "get_environment_A_record", side_effect=error):
                if raises:
                    with self.assertRaises(botocore.exceptions.ClientError):
                        self.route53.create_domain_a_record(hostname=f"bot.{DOMAIN}", api_host_domain=DOMAIN)
                else:
                    self.route53.create_domain_a_record(hostname=f"bot.{DOMAIN}", api_host_domain=DOMAIN)


class TestAWSCertificateManager(AWSTestBase):
    """Test AWSCertificateManager with a fake ACM client."""

    def setUp(self):
        super().setUp()
        self.client = MagicMock()
        self.client.exceptions.ResourceNotFoundException = NotFoundException
        self.acm = connect(AWSCertificateManager(), self.client)
        self.route53_client = FakeRoute53Client()
        self.zone_id = self.route53_client.add_zone(DOMAIN)
        self.acm._route53 = connect(AWSRoute53(), self.route53_client)  # pylint: disable=protected-access
        sleep = patch("smarter.common.helpers.aws.acm.time.sleep")
        self.mock_sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def certificate(self, status="ISSUED", resource_record=True) -> dict:
        option = {"DomainName": DOMAIN}
        if resource_record:
            option["ResourceRecord"] = {"Name": f"_acm.{DOMAIN}", "Type": "CNAME", "Value": "acm-validations.aws."}
        return {"Certificate": {"Status": status, "DomainValidationOptions": [option]}}

    def test_route53(self):
        acm = AWSCertificateManager()
        self.assertIsInstance(acm.route53, AWSRoute53)
        self.assertIs(acm.route53, acm.route53)

    def test_not_ready(self):
        acm = AWSCertificateManager()
        acm._identity = None  # pylint: disable=protected-access
        with patch.object(AWSCertificateManager, "ready", new_callable=PropertyMock, return_value=False):
            for call in (
                lambda: acm.get_certificate_arn(DOMAIN),
                lambda: acm.get_certificate_status("arn"),
                lambda: acm.get_or_create_certificate(DOMAIN),
                lambda: acm.delete_certificate("arn"),
            ):
                with self.assertRaises(AWSNotReadyError):
                    call()

    def test_get_or_create_certificate(self):
        self.client.list_certificates.return_value = {
            "CertificateSummaryList": [{"DomainName": DOMAIN, "CertificateArn": "arn:1"}]
        }
        self.assertEqual(self.acm.get_certificate_arn(DOMAIN), "arn:1")
        self.assertEqual(self.acm.get_or_create_certificate(DOMAIN), "arn:1")
        self.client.request_certificate.assert_not_called()
        self.client.request_certificate.return_value = {"CertificateArn": "arn:2"}
        self.assertEqual(self.acm.get_or_create_certificate("other.example.com"), "arn:2")
        self.client.request_certificate.assert_called_once_with(
            DomainName="other.example.com", ValidationMethod="DNS", SubjectAlternativeNames=["*.other.example.com"]
        )

    def test_get_certificate_status_waits_for_resource_record(self):
        self.client.describe_certificate.side_effect = [
            self.certificate(resource_record=False),
            NotFoundException(),
            self.certificate(),
        ]
        self.assertEqual(self.acm.get_certificate_status("arn"), self.certificate())
        self.assertEqual(self.mock_sleep.call_count, 2)

    def test_get_or_create_certificate_dns_record(self):
        self.client.describe_certificate.return_value = self.certificate()
        record = self.acm.get_or_create_certificate_dns_record("arn")
        self.assertEqual(record["Type"], "CNAME")
        self.assertEqual(record["ResourceRecords"], [{"Value": '"acm-validations.aws."'}])

    def test_verify_certificate(self):
        self.client.describe_certificate.return_value = self.certificate()
        self.assertEqual(self.acm.certificate_status("arn"), "ISSUED")
        self.assertTrue(self.acm.certificate_is_verified("arn"))
        # SUCCESS is the status of a domain's validation, not of the certificate.
        self.client.describe_certificate.return_value = self.certificate("SUCCESS")
        self.assertFalse(self.acm.certificate_is_verified("arn"))
        self.client.describe_certificate.return_value = self.certificate()
        self.assertTrue(self.acm.verify_certificate("arn"))

        self.client.describe_certificate.side_effect = [self.certificate("PENDING_VALIDATION")] * 2 + [
            self.certificate()
        ]
        self.assertTrue(self.acm.verify_certificate("arn"))

        self.client.describe_certificate.side_effect = None
        self.client.describe_certificate.return_value = self.certificate("PENDING_VALIDATION")
        self.assertFalse(self.acm.verify_certificate("arn"))

    def test_get_certificate_status_timeouts(self):
        """Test that waiting for a certificate's DNS records, or for a missing certificate, times out."""
        from smarter.common.helpers.aws.exceptions import (  # pylint: disable=import-outside-toplevel
            AWSACMCertificateNotFound,
            AWSACMVerificationTimeout,
        )

        self.client.describe_certificate.return_value = self.certificate(resource_record=False)
        with self.assertRaises(AWSACMVerificationTimeout):
            self.acm.get_certificate_status("arn")
        self.client.describe_certificate.side_effect = NotFoundException()
        with self.assertRaises(AWSACMCertificateNotFound):
            self.acm.get_certificate_status("arn")

    def test_delete_certificate(self):
        self.acm.delete_certificate("arn")
        self.client.delete_certificate.assert_called_once_with(CertificateArn="arn")
        self.client.delete_certificate.side_effect = NotFoundException()
        self.acm.delete_certificate("arn")  # a missing certificate is not an error


class TestAWSAPIGateway(AWSTestBase):
    """Test AWSAPIGateway with a fake client."""

    def setUp(self):
        super().setUp()
        self.client = MagicMock()
        self.client.exceptions.NotFoundException = NotFoundException
        self.client.get_rest_apis.return_value = {"items": [{"name": "my-api", "id": "api1"}]}
        patcher = patch.object(AWSAPIGateway, "client", new_callable=PropertyMock, return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.gateway = AWSAPIGateway(name="my-api")

    def test_client(self):
        """Test that the client is created once, from the session, with the gateway's timeouts and retries."""
        patch.stopall()  # the client property, and boto3.Session, are tested unpatched.
        gateway = AWSAPIGateway(name="my-api")
        gateway._identity = dict(IDENTITY)  # pylint: disable=protected-access
        session = MagicMock(spec=boto3.Session)
        gateway._aws_session = session  # pylint: disable=protected-access
        self.assertIs(gateway.client, session.client.return_value)
        self.assertIs(gateway.client, session.client.return_value)
        session.client.assert_called_once()
        self.assertEqual(session.client.call_args.args, ("apigateway",))
        self.assertIn("config", session.client.call_args.kwargs)

    def test_client_errors(self):
        patch.stopall()
        gateway = AWSAPIGateway(name="my-api")
        gateway._identity = None  # pylint: disable=protected-access
        with patch.object(AWSAPIGateway, "ready", new_callable=PropertyMock, return_value=False):
            self.assertIsNone(gateway.client)
        gateway._identity = dict(IDENTITY)  # pylint: disable=protected-access
        session = MagicMock(spec=boto3.Session)
        session.client.side_effect = botocore.exceptions.BotoCoreError()
        gateway._aws_session = session  # pylint: disable=protected-access
        self.assertIsNone(gateway.client)

    def test_names(self):
        self.assertEqual(self.gateway.name, "my-api")
        self.assertEqual(self.gateway.shared_resource_identifier, SRI)
        self.assertEqual(self.gateway.api_gateway_name, f"{SRI}-api")
        self.gateway._shared_resource_identifier = None  # pylint: disable=protected-access
        with self.assertRaises(SmarterAWSException):
            _ = self.gateway.api_gateway_name

    def test_apis(self):
        self.assertTrue(self.gateway.api_exists("my-api"))
        self.assertFalse(self.gateway.api_exists("other"))
        self.assertEqual(self.gateway.get_api("my-api")["id"], "api1")
        self.assertEqual(self.gateway.get_api("other"), {})

    def test_get_api_stage(self):
        self.client.get_stages.return_value = {"item": [{"stageName": "v1"}, {"stageName": "v2"}]}
        self.assertEqual(self.gateway.get_api_stage(), "v2")
        self.client.get_stages.return_value = {"item": []}
        self.assertEqual(self.gateway.get_api_stage(), "")
        with self.assertRaises(SmarterAWSException):
            AWSAPIGateway().get_api_stage()

    def test_get_api_custom_domains(self):
        self.client.get_domain_names.return_value = {
            "items": [{"domainName": f"api.{SRI}.example.com"}, {"domainName": "other.com"}, {}]
        }
        self.assertEqual(self.gateway.get_api_custom_domains(), [{"domainName": f"api.{SRI}.example.com"}])

    def test_api_resource_and_method_exists(self):
        self.client.get_resources.return_value = {"items": [{"path": "/chat", "id": "r1"}]}
        self.assertTrue(self.gateway.api_resource_and_method_exists("/chat", "POST"))
        self.assertFalse(self.gateway.api_resource_and_method_exists("/other", "POST"))
        self.client.get_method.side_effect = NotFoundException()
        self.assertFalse(self.gateway.api_resource_and_method_exists("/chat", "POST"))
        with self.assertRaises(SmarterAWSException):
            AWSAPIGateway().api_resource_and_method_exists("/chat", "POST")

    def test_get_api_keys(self):
        self.client.get_api_keys.return_value = {"items": [{"name": SRI, "value": "key"}]}
        self.assertEqual(self.gateway.get_api_keys(), "key")
        self.client.get_api_keys.return_value = {"items": []}
        self.assertIsNone(self.gateway.get_api_keys())


class TestAWSServiceHelpers(AWSTestBase):
    """Test the small AWS helpers, with fake clients."""

    def test_iam(self):
        client = MagicMock()
        client.list_policies.return_value = {
            "Policies": [{"PolicyName": f"{SRI}-policy", "Arn": "arn:p"}, {"PolicyName": "other", "Arn": "arn:o"}]
        }
        client.get_policy.return_value = {"Policy": {"DefaultVersionId": "v1"}}
        client.get_policy_version.return_value = {"PolicyVersion": {"Document": {"Statement": []}}}
        client.list_roles.return_value = {
            "Roles": [{"RoleName": f"{SRI}-role", "Arn": "arn:r"}, {"RoleName": "other", "Arn": "arn:x"}]
        }
        client.list_attached_role_policies.return_value = {"AttachedPolicies": [{"PolicyName": "p"}]}
        iam = connect(AWSIdentifyAccessManagement(), client)
        self.assertEqual(iam.get_iam_policies(), {f"{SRI}-policy": {"Arn": "arn:p", "Policy": {"Statement": []}}})
        roles = iam.get_iam_roles()
        self.assertEqual(list(roles.keys()), [f"{SRI}-role"])
        self.assertEqual(roles[f"{SRI}-role"]["AttachedPolicies"], [{"PolicyName": "p"}])

    def test_s3(self):
        client = MagicMock()
        client.list_buckets.return_value = {"Buckets": [{"Name": "smarter-bucket"}]}
        s3 = connect(AWSSimpleStorageSystem(), client)
        self.assertEqual(s3.get_bucket_by_prefix("smarter"), "arn:aws:s3:::smarter-bucket")
        self.assertTrue(s3.bucket_exists("smarter"))
        self.assertFalse(s3.bucket_exists("other"))
        client.list_buckets.return_value = {"Buckets": None}
        self.assertIsNone(s3.get_bucket_by_prefix("smarter"))

    def test_rds(self):
        client = MagicMock()
        client.describe_db_instances.return_value = {
            "DBInstances": [{"Engine": "mysql", "EngineVersion": "8.0", "Other": 1}]
        }
        self.assertEqual(connect(AWSRds(), client).get_mysql_info(), {"Engine": "mysql", "EngineVersion": "8.0"})

    def test_eks(self):
        client = MagicMock()
        client.describe_cluster.return_value = {
            "cluster": {"health": {}, "platformVersion": "eks.1", "status": "ACTIVE", "version": "1.30"}
        }
        info = connect(AWSEks(), client).get_kubernetes_info()
        self.assertEqual(info["status"], "ACTIVE")
        client.describe_cluster.assert_called_once_with(name=smarter_settings.aws_eks_cluster_name)

    def test_dynamodb(self):
        client = MagicMock()
        client.list_tables.return_value = {"TableNames": ["table"]}
        client.describe_table.return_value = {"Table": {"TableArn": "arn:t"}}
        dynamodb = connect(AWSDynamoDB(), client)
        self.assertEqual(dynamodb.get_dyanmodb_table_by_name("table"), "arn:t")
        self.assertTrue(dynamodb.dynamodb_table_exists("table"))
        self.assertFalse(dynamodb.dynamodb_table_exists("other"))

    def test_rekognition(self):
        client = MagicMock()
        client.list_collections.return_value = {"CollectionIds": ["faces"]}
        rekognition = connect(AWSRekognition(collection_id="faces"), client)
        self.assertEqual(rekognition.collection_id, "faces")
        self.assertTrue(rekognition.rekognition_collection_exists())
        self.assertIsNone(rekognition.get_rekognition_collection_by_id("other"))

    def test_lambda(self):
        client = MagicMock()
        client.list_functions.return_value = {
            "Functions": [
                {"FunctionName": f"{SRI}-fn", "FunctionArn": "arn:f"},
                {"FunctionName": "other", "FunctionArn": "arn:o"},
            ]
        }
        self.assertEqual(connect(AWSLambdaFunction(), client).get_lambdas(), {f"{SRI}-fn": "arn:f"})

    def test_not_ready(self):
        """Test that each helper refuses to call AWS when it is not ready."""
        calls = [
            (AWSIdentifyAccessManagement, lambda h: h.get_iam_policies()),
            (AWSIdentifyAccessManagement, lambda h: h.get_iam_roles()),
            (AWSSimpleStorageSystem, lambda h: h.get_bucket_by_prefix("x")),
            (AWSRds, lambda h: h.get_mysql_info()),
            (AWSEks, lambda h: h.get_kubernetes_info()),
            (AWSRekognition, lambda h: h.get_rekognition_collection_by_id("x")),
            (AWSLambdaFunction, lambda h: h.get_lambdas()),
        ]
        for helper_class, call in calls:
            with self.subTest(helper=helper_class.__name__):
                with patch.object(helper_class, "ready", new_callable=PropertyMock, return_value=False):
                    with self.assertRaises(AWSNotReadyError):
                        call(helper_class())
