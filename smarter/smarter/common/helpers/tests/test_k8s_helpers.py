# pylint: disable=wrong-import-position
"""
Test k8s_helper class.

WARNINGS:
- depends on k8s namespace smarter-platform-alpha
- leaving the DNS resources in place permanently as it takes 15+ minutes to propagate
"""

# python stuff
import os
import time
from string import Template

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.k8s_helpers import kubernetes_helper
from smarter.lib.unittest.base_classes import SmarterTestBase


HERE = os.path.abspath(os.path.dirname(__file__))


class Testk8sHelpers(SmarterTestBase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        self.environment = SmarterEnvironments.ALPHA
        self.api_domain = f"{self.environment}.api.{smarter_settings.root_domain}"
        self.cluster_issuer = self.api_domain
        self.account_number = SMARTER_ACCOUNT_NUMBER
        self.hostname = f"{self.name}.{self.account_number}.{self.cluster_issuer}"
        self.namespace = f"{smarter_settings.platform_name}-platform-{self.environment}"

        # get-or-create the top-level api domain: alpha.api.smarter.sh
        aws_helper.route53.create_domain_a_record(
            hostname=self.api_domain, api_host_domain=smarter_settings.root_domain
        )
        # get-or-create the subdomain for the test: ty7xlk2i.alpha.api.smarter.sh
        aws_helper.route53.create_domain_a_record(hostname=self.hostname, api_host_domain=self.api_domain)

        # verify the DNS records. First time usage takes 15+ minutes to propagate
        # assuming you're not inside the aws vpc. Subsequent runs are near-immediate.
        aws_helper.route53.verify_dns_record(self.hostname)

    def tearDown(self):
        """Clean up test fixtures."""

    def test_kubeconfig(self):
        """Test kubeconfig property."""
        kubeconfig = kubernetes_helper.kubeconfig
        self.assertIsInstance(kubeconfig, dict)

    def test_update_kubeconfig(self):
        """Test update_kubeconfig method."""

        kubernetes_helper.update_kubeconfig()

    def test_get_namespaces(self):
        """Test get_namespaces method."""
        output = kubernetes_helper.get_namespaces()
        self.assertIsInstance(output, dict)

    def test_verify_ingress(self):
        """
        Test verify_ingress method.
        verifying an existing ingress.
        """
        name = "smarter.3141-5926-5359.alpha.api.smarter.sh"
        output = kubernetes_helper.verify_ingress(name, self.namespace)
        self.assertTrue(output)

    def test_verify_certificate(self):
        """
        Test verify_certificate method.
        verifying an existing certificate
        """
        name = "smarter.3141-5926-5359.alpha.api.smarter.sh-tls"
        output = kubernetes_helper.verify_certificate(name, self.namespace)
        self.assertTrue(output)

    def test_verify_secret(self):
        """
        Test verify_secret method
        verifying an existing secret
        """
        name = "smarter.3141-5926-5359.alpha.api.smarter.sh-tls"
        output = kubernetes_helper.verify_secret(name, self.namespace)
        self.assertTrue(output)

    def test_apply_manifest(self):
        """
        Test that we can apply a manifest that creates
        a new ingress with a certificate and secret.
        """
        ingress_values = {
            "cluster_issuer": self.cluster_issuer,
            "environment_namespace": self.namespace,
            "domain": self.hostname,
            "service_name": smarter_settings.platform_name,
        }

        # create and apply the ingress manifest
        template_path = os.path.join(HERE, "./data/ingress.yaml.tpl")
        with open(template_path, encoding="utf-8") as ingress_template:
            template = Template(ingress_template.read())
            manifest = template.substitute(ingress_values)
        kubernetes_helper.apply_manifest(manifest)
        time.sleep(10)
        output = kubernetes_helper.verify_ingress(self.hostname, self.namespace)
        self.assertTrue(output)

    # def test_verify_ingress_resources(self):
    #     """Test verify_ingress_resources method."""

    #     ingress_verified, certificate_verified, secret_verified = kubernetes_helper.verify_ingress_resources(
    #         self.hostname, self.namespace
    #     )
    #     self.assertTrue(ingress_verified)
    #     self.assertTrue(certificate_verified)
    #     self.assertTrue(secret_verified)

    # def test_delete_ingress_resources(self):
    #     """Test delete_ingress_resources method."""

    #     ingress_deleted, certificate_deleted, secret_deleted = kubernetes_helper.delete_ingress_resources(
    #         self.hostname, self.namespace
    #     )
    #     self.assertTrue(ingress_deleted)
    #     self.assertTrue(certificate_deleted)
    #     self.assertTrue(secret_deleted)
