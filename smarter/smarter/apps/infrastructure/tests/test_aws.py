"""
Test the AWS provider, :mod:`smarter.apps.infrastructure.providers.aws`, and its low-level helpers.

None of these tests reach AWS. The helpers' boto3 clients are fakes, :class:`FakeRoute53Client`
and :class:`FakeACMClient`, which answer like boto3, the helpers' identity is set, and the
check that AWS is configured, which calls STS, is patched. boto3.Session is patched, so that a
test that forgot a fake fails rather than use the container's live AWS credentials.
"""

import base64
import os
import subprocess
import time
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import parse_qs, urlparse

import boto3
import botocore.exceptions

from smarter.apps.infrastructure.const import CertificateStatus, CloudProviders
from smarter.apps.infrastructure.exceptions import (
    InfrastructureConfigurationError,
    InfrastructureNotReadyError,
)
from smarter.apps.infrastructure.providers.aws import AWSProvider
from smarter.apps.infrastructure.providers.aws.certificates import to_certificate
from smarter.apps.infrastructure.providers.aws.dns import to_record, to_record_set
from smarter.apps.infrastructure.providers.aws.helpers.acm import AWSCertificateManager
from smarter.apps.infrastructure.providers.aws.helpers.base import AWSBase
from smarter.apps.infrastructure.providers.aws.helpers.eks import (
    EKS_TOKEN_LIFETIME_SECONDS,
    AWSEks,
)
from smarter.apps.infrastructure.providers.aws.helpers.exceptions import (
    AWSNotReadyError,
    SmarterAWSError,
)
from smarter.apps.infrastructure.providers.aws.helpers.route53 import (
    AWSRoute53,
    hosted_zone_id,
)
from smarter.apps.infrastructure.services.dns import DNSRecord
from smarter.apps.infrastructure.signals import (
    infrastructure_authenticated,
    infrastructure_authentication_failed,
    infrastructure_connected,
)
from smarter.lib import json

from .base import InfrastructureTestBase

AWS = "smarter.apps.infrastructure.providers.aws"
HELPERS = f"{AWS}.helpers"
IDENTITY = {"UserId": "AIDATEST", "Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"}
HERE = os.path.abspath(os.path.dirname(__file__))
CERTIFICATE_DETAIL = os.path.join(HERE, "data", "acm_certificate_detail.json")
BOTO3_SESSION = boto3.Session
"""The real boto3.Session class, which the tests patch, for the helpers' isinstance() check."""


class NotFound(Exception):
    """A fake boto3 client's NoSuchHostedZone / ResourceNotFoundException."""


class Paginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return self.pages(**kwargs)


class FakeRoute53Client:
    """An in-memory Route53 client: hosted zones, their delegation sets, and their record sets."""

    exceptions = MagicMock(NoSuchHostedZone=NotFound)

    def __init__(self):
        self.zones: dict[str, dict] = {}
        self.records: dict[str, list[dict]] = {}
        self.changes: list[tuple[str, dict]] = []

    def create_hosted_zone(self, Name, CallerReference, HostedZoneConfig):  # pylint: disable=invalid-name
        zone_id = f"Z{len(self.zones) + 1}"
        zone = {"Id": f"/hostedzone/{zone_id}", "Name": f"{Name.rstrip('.')}."}
        name_servers = [f"ns-{zone_id}-{i}.awsdns.com" for i in (1, 2)]
        self.zones[zone_id] = {"HostedZone": zone, "DelegationSet": {"NameServers": name_servers}}
        self.records[zone_id] = [
            {
                "Name": zone["Name"],
                "Type": "NS",
                "TTL": 172800,
                "ResourceRecords": [{"Value": f"{n}."} for n in name_servers],
            },
            {"Name": zone["Name"], "Type": "SOA", "TTL": 900, "ResourceRecords": [{"Value": "soa"}]},
        ]
        return self.zones[zone_id]

    def get_hosted_zone(self, Id):  # pylint: disable=invalid-name
        if Id not in self.zones:
            raise NotFound(Id)
        return self.zones[Id]

    def delete_hosted_zone(self, Id):  # pylint: disable=invalid-name
        self.zones.pop(Id)
        self.records.pop(Id)

    def get_paginator(self, name):
        if name == "list_hosted_zones":
            return Paginator(lambda: [{"HostedZones": [z["HostedZone"] for z in self.zones.values()]}])
        return Paginator(lambda HostedZoneId: [{"ResourceRecordSets": list(self.records[HostedZoneId])}])

    def change_resource_record_sets(self, HostedZoneId, ChangeBatch):  # pylint: disable=invalid-name
        for change in ChangeBatch["Changes"]:
            record_set = change["ResourceRecordSet"]
            self.changes.append((change["Action"], record_set))
            records = self.records[HostedZoneId]
            key = (record_set["Name"].rstrip("."), record_set["Type"])
            records[:] = [r for r in records if (r["Name"].rstrip("."), r["Type"]) != key]
            if change["Action"] in ("CREATE", "UPSERT"):
                records.append({**record_set, "Name": f"{record_set['Name'].rstrip('.')}."})


class FakeACMClient:
    """An in-memory ACM client."""

    exceptions = MagicMock(ResourceNotFoundException=NotFound)

    def __init__(self):
        with open(CERTIFICATE_DETAIL, encoding="utf-8") as detail:
            self.template = json.loads(detail.read())["Certificate"]
        self.certificates: dict[str, dict] = {}

    def get_paginator(self, name):
        return Paginator(
            lambda: [
                {
                    "CertificateSummaryList": [
                        {"DomainName": c["DomainName"], "CertificateArn": arn} for arn, c in self.certificates.items()
                    ]
                }
            ]
        )

    def request_certificate(
        self, DomainName, ValidationMethod, SubjectAlternativeNames
    ):  # pylint: disable=invalid-name
        arn = f"arn:aws:acm:us-east-1:123456789012:certificate/{len(self.certificates) + 1}"
        certificate = {**self.template, "CertificateArn": arn, "DomainName": DomainName, "Status": "PENDING_VALIDATION"}
        self.certificates[arn] = certificate
        return {"CertificateArn": arn}

    def describe_certificate(self, CertificateArn):  # pylint: disable=invalid-name
        if CertificateArn not in self.certificates:
            raise NotFound(CertificateArn)
        return {"Certificate": self.certificates[CertificateArn]}

    def delete_certificate(self, CertificateArn):  # pylint: disable=invalid-name
        if CertificateArn not in self.certificates:
            raise NotFound(CertificateArn)
        del self.certificates[CertificateArn]


def connect(helper: AWSBase, client: Any) -> AWSBase:
    """Give a helper a fake client and identity, so that it is ready without AWS."""
    helper._client = client  # pylint: disable=protected-access
    helper._identity = dict(IDENTITY)  # pylint: disable=protected-access
    return helper


class AWSTestBase(InfrastructureTestBase):
    """Patch boto3.Session and the STS configuration check, so that no test can reach AWS."""

    def setUp(self):
        super().setUp()
        for target in (f"{HELPERS}.base.boto3.Session", f"{HELPERS}.base.services"):
            patcher = patch(target)
            setattr(self, target.rsplit(".", 1)[-1].lower(), patcher.start())
            self.addCleanup(patcher.stop)
        self.route53_client = FakeRoute53Client()
        self.acm_client = FakeACMClient()

    def aws_provider(self) -> AWSProvider:
        """An AWS provider whose helpers have fake clients."""
        provider = AWSProvider(allow_in_tests=True)
        provider._base = connect(AWSBase(), MagicMock())  # pylint: disable=protected-access
        # aws_session returns None without credentials, as in CI, so give it the patched session.
        provider._base._aws_session = self.session.return_value  # pylint: disable=protected-access
        route53 = connect(AWSRoute53(), self.route53_client)
        acm = connect(AWSCertificateManager(), self.acm_client)
        provider.dns._route53 = route53  # pylint: disable=protected-access
        provider.certificates._acm = acm  # pylint: disable=protected-access
        provider.dns.record_wait_seconds = 0
        provider.certificates.validation_wait_seconds = 0
        return provider


class TestAWSProvider(AWSTestBase):
    """Test the AWS provider's authentication, guard, and cluster operations."""

    def test_refused_in_unit_tests(self):
        """The AWS provider never reaches AWS from the unit tests, unless it is allowed to."""
        provider = AWSProvider()
        self.assertEqual(provider.name, CloudProviders.AWS)
        self.assertFalse(provider.ready)
        self.assertIsNone(provider.identity)
        self.assertIsNone(provider.account_id)
        self.assertFalse(provider.update_kubeconfig())
        with self.assertRaises(InfrastructureConfigurationError):
            provider.base  # pylint: disable=pointless-statement
        with self.assertRaises(InfrastructureConfigurationError):
            provider.eks  # pylint: disable=pointless-statement
        with self.assertRaises(InfrastructureConfigurationError):
            provider.dns.route53  # pylint: disable=pointless-statement
        with self.assertRaises(InfrastructureConfigurationError):
            provider.certificates.acm  # pylint: disable=pointless-statement
        self.assertFalse(provider.dns.ready)
        self.assertEqual(provider.sdk_version, boto3.__version__)

    def test_authenticated(self):
        events = self.capture(infrastructure_authenticated)
        provider = self.aws_provider()
        self.assertTrue(provider.ready)
        self.assertEqual(provider.account_id, "123456789012")
        self.assertEqual(self.sent(events, infrastructure_authenticated)[0]["identity"], IDENTITY)
        self.assertIsNotNone(provider.session)

    def test_not_authenticated(self):
        events = self.capture(infrastructure_authentication_failed)
        provider = AWSProvider(allow_in_tests=True)
        with patch.object(AWSBase, "identity", new_callable=PropertyMock, return_value=None):
            self.assertFalse(provider.ready)
        with patch.object(AWSBase, "identity", new_callable=PropertyMock, side_effect=RuntimeError("expired")):
            self.assertFalse(provider.ready)
        self.assertEqual(len(self.sent(events, infrastructure_authentication_failed)), 1)

    def test_kubernetes_cluster(self):
        provider = self.aws_provider()
        eks = connect(AWSEks(), MagicMock())
        eks.client.describe_cluster.return_value = {
            "cluster": {"health": {}, "platformVersion": "eks.1", "status": "ACTIVE", "version": "1.33", "other": 1}
        }
        provider._eks = eks  # pylint: disable=protected-access
        # set the cluster name here, so the test does not depend on the environment's .env.
        with patch(f"{HELPERS}.eks.smarter_settings") as settings:
            settings.aws_eks_cluster_name = "cluster"
            self.assertEqual(
                provider.get_kubernetes_cluster_info(),
                {"health": {}, "platformVersion": "eks.1", "status": "ACTIVE", "version": "1.33"},
            )
        eks.client.describe_cluster.assert_called_once_with(name="cluster")
        with patch.object(AWSEks, "update_kubeconfig", return_value=True):
            self.assertTrue(provider.update_kubeconfig())

    def test_kubernetes_cluster_not_ready(self):
        with self.assertRaises(InfrastructureNotReadyError):
            AWSProvider().get_kubernetes_cluster_info()

    def test_lazy_helpers(self):
        provider = AWSProvider(allow_in_tests=True)
        self.assertIsInstance(provider.base, AWSBase)
        self.assertIs(provider.base, provider.base)
        self.assertIsInstance(provider.eks, AWSEks)
        self.assertIs(provider.dns, provider.dns)
        self.assertIs(provider.certificates.dns, provider.dns)


class TestRoute53DNSService(AWSTestBase):
    """Test the platform's DNS operations, through Route53DNSService, the Route53 helper and a fake client."""

    def setUp(self):
        super().setUp()
        self.provider = self.aws_provider()
        self.dns = self.provider.dns

    def test_zones(self):
        zone, created = self.dns.get_or_create_zone("example.com")
        self.assertTrue(created)
        self.assertEqual((zone.id, zone.name), ("Z1", "example.com"))
        self.assertEqual(zone.name_servers, ["ns-z1-1.awsdns.com", "ns-z1-2.awsdns.com"])
        self.assertEqual(self.dns.get_zone("example.com").id, "Z1")
        # ids with Route53's /hostedzone/ prefix, which older rows store, work too.
        self.assertEqual(self.dns.get_zone_by_id("/hostedzone/Z1").name, "example.com")
        self.assertEqual(self.dns.get_name_servers("Z1"), zone.name_servers)
        self.assertIsNone(self.dns.get_zone_by_id("ZNOPE"))
        self.assertIsNone(self.dns.get_zone("other.com"))

    def test_records(self):
        zone, _ = self.dns.get_or_create_zone("example.com")
        record, created = self.dns.get_or_create_record(zone.id, "www.example.com", "A", ttl=300, values=["192.0.2.1"])
        self.assertTrue(created)
        self.assertEqual(self.route53_client.changes[-1][0], "CREATE")
        self.assertEqual(record, DNSRecord(name="www.example.com", type="A", ttl=300, values=["192.0.2.1"]))
        _, created = self.dns.get_or_create_record(zone.id, "www.example.com", "A", ttl=300, values=["192.0.2.2"])
        self.assertFalse(created)
        self.assertEqual(self.route53_client.changes[-1][0], "UPSERT")
        self.assertTrue(self.dns.delete_record(zone.id, "www.example.com", "A"))
        action, record_set = self.route53_client.changes[-1]
        self.assertEqual(action, "DELETE")
        self.assertEqual(record_set["ResourceRecords"], [{"Value": "192.0.2.2"}])

    def test_txt_and_validation_records(self):
        """TXT values are quoted for Route53, and unquoted for the platform.

        CNAME values are not quoted.
        """
        zone, _ = self.dns.get_or_create_zone("example.com")
        record, _ = self.dns.get_or_create_record(zone.id, "_acme-challenge.example.com", "TXT", values=["token"])
        self.assertEqual(record.values, ["token"])
        self.assertEqual(self.route53_client.changes[-1][1]["ResourceRecords"], [{"Value": '"token"'}])
        self.dns.get_or_create_record(zone.id, "_x1.example.com", "CNAME", values=["_x2.acm-validations.aws."])
        self.assertEqual(self.route53_client.changes[-1][1]["ResourceRecords"], [{"Value": "_x2.acm-validations.aws."}])

    def test_create_domain_a_record_with_alias(self):
        """The environment's alias A record, e.g. its load balancer, is copied as an alias."""
        zone, _ = self.dns.get_or_create_zone("api.example.com")
        alias = {"HostedZoneId": "ZLB", "DNSName": "lb.elb.amazonaws.com.", "EvaluateTargetHealth": True}
        self.dns.get_or_create_record(zone.id, "api.example.com", "A", alias=alias)
        record, created = self.dns.create_domain_a_record("app.api.example.com", "api.example.com")
        self.assertTrue(created)
        self.assertEqual(record.alias, alias)
        self.assertNotIn("TTL", self.route53_client.changes[-1][1])

    def test_delete_zone(self):
        """A zone's own records are deleted first: Route53 refuses to delete a zone that has others."""
        zone, _ = self.dns.get_or_create_zone("example.com")
        self.dns.get_or_create_record(zone.id, "www.example.com", "A", values=["192.0.2.1"])
        self.assertTrue(self.dns.delete_zone("example.com"))
        self.assertEqual(self.route53_client.zones, {})
        deleted = [record_set["Type"] for action, record_set in self.route53_client.changes if action == "DELETE"]
        self.assertEqual(deleted, ["A"])

    def test_connected_once(self):
        events = self.capture(infrastructure_connected)
        provider = AWSProvider(allow_in_tests=True)
        with patch(f"{AWS}.dns.AWSRoute53") as helper_class:
            self.assertIs(provider.dns.route53, helper_class.return_value)
            self.assertIs(provider.dns.route53, helper_class.return_value)
        helper_class.assert_called_once()
        self.assertEqual(len(self.sent(events, infrastructure_connected)), 1)

    def test_conversions(self):
        record = to_record({"Name": "a.example.com.", "Type": "txt", "TTL": 60, "ResourceRecords": [{"Value": '"x"'}]})
        self.assertEqual((record.name, record.type, record.values), ("a.example.com", "TXT", ["x"]))
        self.assertEqual(to_record_set(record)["ResourceRecords"], [{"Value": '"x"'}])
        self.assertEqual(hosted_zone_id("/hostedzone/Z9"), "Z9")


class TestACMCertificateService(AWSTestBase):
    """Test the platform's certificate operations, through ACMCertificateService, the ACM helper and a fake client."""

    def setUp(self):
        super().setUp()
        self.provider = self.aws_provider()
        self.certificates = self.provider.certificates

    def test_certificate_lifecycle(self):
        certificate_id, created = self.certificates.get_or_create_certificate("example.com")
        self.assertTrue(created)
        self.assertEqual(self.certificates.get_certificate_id("example.com"), certificate_id)
        self.assertEqual(self.certificates.certificate_status(certificate_id), "PENDING_VALIDATION")

        # the domain's and its wildcard's validation records, from ACM's DomainValidationOptions.
        records = self.certificates.create_validation_records(certificate_id)
        self.assertEqual([r.name for r in records], ["_x1.example.com", "_x3.example.com"])
        zone = self.provider.dns.get_zone("example.com")
        self.assertEqual(
            self.provider.dns.get_record(zone.id, "_x1.example.com", "CNAME").values, ["_x2.acm-validations.aws."]
        )

        self.acm_client.certificates[certificate_id]["Status"] = "ISSUED"
        self.assertTrue(self.certificates.is_issued(certificate_id))
        self.assertTrue(self.certificates.delete_certificate(certificate_id))
        self.assertFalse(self.certificates.delete_certificate(certificate_id))

    def test_to_certificate(self):
        with open(CERTIFICATE_DETAIL, encoding="utf-8") as detail:
            certificate = to_certificate(json.loads(detail.read())["Certificate"])
        self.assertEqual(certificate.domain_name, "example.com")
        self.assertEqual(len(certificate.validation_records), 2)
        self.assertFalse(certificate.is_issued)
        self.assertEqual(
            to_certificate(
                {"CertificateArn": "a", "DomainName": "d", "Status": CertificateStatus.ISSUED}
            ).validation_records,
            [],
        )

    def test_helper_delete_missing_certificate(self):
        """The helper treats a certificate that does not exist as deleted."""
        self.certificates.acm.delete_certificate("arn:missing")


class TestAWSHelpers(AWSTestBase):
    """Test the low-level helpers' readiness checks."""

    def test_not_ready(self):
        for helper, attribute in ((AWSRoute53(), "route53"), (AWSCertificateManager(), "acm")):
            with self.subTest(helper=type(helper).__name__):
                with patch.object(type(helper), "ready", new_callable=PropertyMock, return_value=False):
                    with self.assertRaises(AWSNotReadyError):
                        getattr(helper, attribute)
        with patch.object(AWSEks, "ready", new_callable=PropertyMock, return_value=False):
            with self.assertRaises(AWSNotReadyError):
                AWSEks().get_kubernetes_info()

    def test_update_kubeconfig(self):
        eks = AWSEks()
        with (
            patch(f"{HELPERS}.eks.smarter_settings") as settings,
            patch(f"{HELPERS}.eks.subprocess.check_call") as call,
        ):
            settings.aws_eks_cluster_name = "cluster"
            settings.aws_region = "us-east-1"
            self.assertTrue(eks.update_kubeconfig())
            self.assertEqual(call.call_args.args[0][:3], ["aws", "eks", "update-kubeconfig"])
            call.side_effect = subprocess.CalledProcessError(1, "aws")
            self.assertFalse(eks.update_kubeconfig())
            settings.aws_eks_cluster_name = None
            self.assertFalse(eks.update_kubeconfig())

    def test_missing_cluster_name_is_logged_once(self):
        """Without a cluster name, nothing reaches EKS, and how to set it is logged once per process."""
        eks = connect(AWSEks(), MagicMock())
        with (
            patch(f"{HELPERS}.eks.smarter_settings") as settings,
            patch(f"{HELPERS}.eks.subprocess.check_call") as call,
            patch(f"{HELPERS}.eks.logger") as logger,
            patch.object(AWSEks, "_cluster_name_warned", False),
        ):
            settings.aws_eks_cluster_name = None
            self.assertFalse(eks.update_kubeconfig())
            self.assertFalse(eks.update_kubeconfig())
            with self.assertRaises(AWSNotReadyError):
                eks.get_kubernetes_info()
        call.assert_not_called()
        eks.client.describe_cluster.assert_not_called()
        logger.error.assert_called_once()
        self.assertIn("SMARTER_AWS_EKS_CLUSTER_NAME", logger.error.call_args.args[0])

    def test_get_kubernetes_info(self):
        eks = connect(AWSEks(), MagicMock())
        eks.client.describe_cluster.return_value = {"cluster": {"status": "ACTIVE", "version": "1.33"}}
        with patch(f"{HELPERS}.eks.smarter_settings") as settings:
            settings.aws_eks_cluster_name = "cluster"
            info = eks.get_kubernetes_info()
        eks.client.describe_cluster.assert_called_once_with(name="cluster")
        self.assertEqual(info["status"], "ACTIVE")

    def test_get_token(self):
        """The EKS token is an STS GetCallerIdentity url, presigned for the cluster, as aws eks get-token creates."""
        eks = connect(AWSEks(), MagicMock())
        # boto3.Session is patched; boto3.session.Session is not. Presigning makes no request.
        eks._aws_session = boto3.session.Session(  # pylint: disable=protected-access
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",  # nosec B106
            region_name="ca-central-1",
        )
        eks._aws_region = "ca-central-1"  # pylint: disable=protected-access
        with patch(f"{HELPERS}.eks.smarter_settings") as settings:
            settings.aws_eks_cluster_name = "cluster"
            before = time.time()
            token, expires = eks.get_token()
        self.assertTrue(token.startswith("k8s-aws-v1."))
        encoded = token.removeprefix("k8s-aws-v1.")
        url = urlparse(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8"))
        query = parse_qs(url.query)
        self.assertEqual(url.netloc, "sts.ca-central-1.amazonaws.com")
        self.assertEqual(query["Action"], ["GetCallerIdentity"])
        self.assertEqual(query["X-Amz-Expires"], ["60"])
        self.assertIn("x-k8s-aws-id", query["X-Amz-SignedHeaders"][0])
        self.assertTrue(query["X-Amz-Credential"][0].startswith("AKIAIOSFODNN7EXAMPLE/"))
        self.assertAlmostEqual(expires, before + EKS_TOKEN_LIFETIME_SECONDS, delta=5)

    def test_get_token_not_ready(self):
        eks = AWSEks()
        with patch(f"{HELPERS}.eks.smarter_settings") as settings:
            settings.aws_eks_cluster_name = None
            with self.assertRaises(AWSNotReadyError):
                eks.get_token()

    def test_provider_kubernetes_token(self):
        """The provider returns the EKS token, or None, for kubectl to fall back to its kubeconfig."""
        self.assertIsNone(AWSProvider().get_kubernetes_token())
        provider = self.aws_provider()
        provider._eks = connect(AWSEks(), MagicMock())  # pylint: disable=protected-access
        with patch.object(AWSEks, "get_token", return_value=("token", 1.0)):
            self.assertEqual(provider.get_kubernetes_token(), ("token", 1.0))
        with patch.object(AWSEks, "get_token", side_effect=AWSNotReadyError("no cluster")):
            self.assertIsNone(provider.get_kubernetes_token())

    def test_exceptions(self):
        self.assertTrue(issubclass(AWSNotReadyError, InfrastructureNotReadyError))
        self.assertTrue(issubclass(SmarterAWSError, Exception))


class TestAWSBase(AWSTestBase):
    """Test AWSBase's authentication, session and identity."""

    def settings(self, **overrides) -> MagicMock:
        settings = MagicMock(
            aws_access_key_id=None,
            aws_secret_access_key=None,
            aws_region="us-east-1",
            aws_profile=None,
            debug_mode=False,
        )
        for key, value in overrides.items():
            setattr(settings, key, value)
        return settings

    def base(self, aws_deployed: bool = False, **settings) -> AWSBase:
        with (
            patch(f"{HELPERS}.base.smarter_settings", self.settings(**settings)),
            patch.dict(os.environ, {"AWS_DEPLOYED": "1"} if aws_deployed else {}),
        ):
            if not aws_deployed:
                os.environ.pop("AWS_DEPLOYED", None)
            return AWSBase()

    def test_not_initialized(self):
        base = self.base()
        self.assertFalse(base.authentication_credentials_are_initialized)
        self.assertIsNone(base.aws_session)
        self.assertIsNone(base.identity)
        self.assertFalse(base.ready)
        self.assertIsNone(base.aws_account_id)
        self.assertIsNone(base.aws_iam_arn)
        self.assertIn("not", base.authentication_credentials_state.lower())

    def test_profile(self):
        base = self.base(aws_profile="smarter")
        self.assertEqual(base.aws_access_key_id_source, "aws_profile")
        self.assertIs(base.aws_session, self.session.return_value)
        self.session.assert_called_with(profile_name="smarter", region_name="us-east-1")

    def test_missing_profile_falls_back(self):
        self.session.side_effect = [botocore.exceptions.ProfileNotFound(profile="smarter"), MagicMock()]
        base = self.base(aws_profile="smarter")
        self.assertIsNotNone(base.aws_session)

    def test_key_pair(self):
        base = self.base(aws_access_key_id=MagicMock(), aws_secret_access_key=MagicMock())
        self.assertEqual(base.aws_access_key_id_source, "passed parameter")
        self.assertIsNotNone(base.aws_session)
        self.assertEqual(base.aws_auth["aws_region"], "us-east-1")

    def test_key_pair_error(self):
        self.session.side_effect = [RuntimeError("bad keys"), RuntimeError("no credentials")]
        base = self.base(aws_access_key_id=MagicMock(), aws_secret_access_key=MagicMock())
        self.assertIsNone(base.aws_session)

    def test_aws_deployed(self):
        """Inside AWS, IAM role-based security replaces the credentials."""
        base = self.base(aws_deployed=True)
        self.assertEqual(base.aws_access_key_id_source, "overridden by IAM role-based security")
        with patch.dict(os.environ, {"AWS_DEPLOYED": "1"}):
            self.assertTrue(base.is_aws_deployed)

    def test_identity(self):
        base = self.base(aws_profile="smarter")
        self.session.return_value.client.return_value.get_caller_identity.return_value = IDENTITY
        self.assertEqual(base.identity, IDENTITY)
        self.assertTrue(base.ready)
        self.assertEqual(base.aws_account_id, "123456789012")
        self.assertEqual(base.aws_iam_arn, IDENTITY["Arn"])
        # cached.
        self.session.return_value.client.return_value.get_caller_identity.side_effect = RuntimeError("no")
        self.assertEqual(base.identity, IDENTITY)

    def test_identity_error(self):
        base = self.base(aws_profile="smarter")
        self.session.return_value.client.return_value.get_caller_identity.side_effect = RuntimeError("expired")
        self.assertIsNone(base.identity)

    def test_client(self):
        base = connect(self.base(aws_profile="smarter"), None)
        with self.assertRaises(SmarterAWSError):
            base.client  # pylint: disable=pointless-statement
        base._client_type = "sts"  # pylint: disable=protected-access
        with patch(f"{HELPERS}.base.boto3.Session", BOTO3_SESSION):
            # a session that is not a boto3.Session gives no client.
            base._aws_session = MagicMock()  # pylint: disable=protected-access
            self.assertIsNone(base.client)
            session = MagicMock(spec=BOTO3_SESSION)
            base._aws_session = session  # pylint: disable=protected-access
            self.assertIs(base.client, session.client.return_value)
            base._client = None  # pylint: disable=protected-access
            session.client.side_effect = botocore.exceptions.BotoCoreError()
            self.assertIsNone(base.client)

    def test_client_not_ready(self):
        base = self.base()
        base._client_type = "sts"  # pylint: disable=protected-access
        self.assertIsNone(base.client)

    def test_properties(self):
        base = self.base(aws_profile="smarter", debug_mode=True)
        self.assertEqual(base.aws_profile, "smarter")
        self.assertEqual(base.aws_region, "us-east-1")
        self.assertTrue(base.debug_mode)
        self.assertTrue(base.version)
        self.assertIsNotNone(base.shared_resource_identifier)
        self.assertIsNotNone(base.environment)
        self.assertIsNotNone(base.root_domain)
        self.assertIsNone(base.aws_secret_access_key)
        self.assertEqual(base.aws_secret_access_key_source, "aws_profile")
        self.assertIn("AWSBase", base.formatted_class_name)

    def test_init_info(self):
        with patch(f"{HELPERS}.base.smarter_settings", self.settings()):
            base = AWSBase(aws_region="eu-west-1", debug_mode=True, init_info="test")
        self.assertEqual(base.aws_region, "eu-west-1")
