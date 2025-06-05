# pylint: disable=wrong-import-position
"""
Test k8s_helper class.

WARNINGS:
- depends on k8s namespace smarter-platform-alpha
- leaving the DNS resources in place permanently as it takes 15+ minutes to propagate
"""

import os

# python stuff
import subprocess
import time
from string import Template
from unittest.mock import MagicMock, patch

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.helpers.k8s_helpers import (
    KubernetesHelper,
    KubernetesHelperException,
    kubernetes_helper,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


HERE = os.path.abspath(os.path.dirname(__file__))


class Testk8sHelpers(SmarterTestBase):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.environment = SmarterEnvironments.LOCAL
        self.api_domain = f"{self.environment}.api.{smarter_settings.root_domain}"
        self.cluster_issuer = self.api_domain
        self.account_number = SMARTER_ACCOUNT_NUMBER
        self.hostname = f"test-k8s-helpers.{self.account_number}.{self.cluster_issuer}"
        self.namespace = f"{smarter_settings.platform_name}-platform-{self.environment}"
        self.helper = KubernetesHelper()

        # get-or-create the subdomain for the test: ty7xlk2i.alpha.api.smarter.sh
        aws_helper.route53.create_domain_a_record(hostname=self.hostname, api_host_domain=self.api_domain)

        # verify the DNS records. First time usage takes 15+ minutes to propagate
        # assuming you're not inside the aws vpc. Subsequent runs are near-immediate.
        aws_helper.route53.verify_dns_record(self.hostname)

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.Popen")
    def test_apply_manifest_success(self, mock_popen, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        process = MagicMock()
        process.communicate.return_value = (b"", b"")
        process.returncode = 0
        mock_popen.return_value.__enter__.return_value = process
        self.helper._configured = True
        self.helper.apply_manifest("apiVersion: v1\nkind: Pod\n")
        process.communicate.assert_called()

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.Popen")
    def test_apply_manifest_failure(self, mock_popen, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        process = MagicMock()
        process.communicate.return_value = (b"", b"error")
        process.returncode = 1
        mock_popen.return_value.__enter__.return_value = process
        self.helper._configured = True
        with self.assertRaises(Exception):
            self.helper.apply_manifest("apiVersion: v1\nkind: Pod\n")

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.check_output")
    def test_verify_ingress_success(self, mock_check_output, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        mock_check_output.return_value = b'{"kind": "Ingress"}'
        self.helper._configured = True
        result = self.helper.verify_ingress("ingress", "ns")
        self.assertTrue(result)

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.check_output")
    def test_verify_ingress_not_found(self, mock_check_output, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")
        self.helper._configured = True
        result = self.helper.verify_ingress("ingress", "ns")
        self.assertFalse(result)

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.check_output")
    def test_verify_secret_success(self, mock_check_output, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        mock_check_output.return_value = b'{"kind": "Secret"}'
        self.helper._configured = True
        result = self.helper.verify_secret("secret", "ns")
        self.assertTrue(result)

    @patch("smarter.common.helpers.k8s_helpers.smarter_settings")
    @patch("smarter.common.helpers.k8s_helpers.formatted_text")
    @patch("smarter.common.helpers.k8s_helpers.logger")
    @patch("smarter.common.helpers.k8s_helpers.subprocess.check_output")
    def test_verify_secret_not_found(self, mock_check_output, mock_logger, mock_formatted_text, mock_settings):
        mock_settings.aws_eks_cluster_name = "test"
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "cmd")
        self.helper._configured = True
        result = self.helper.verify_secret("secret", "ns")
        self.assertFalse(result)

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

    def test_apply_illegal_host_name(self):
        """
        Test that we can apply a manifest that creates
        a new ingress with a certificate and secret.
        """
        bad_hostname = f"test_k8s_helpers.{self.account_number}.{self.cluster_issuer}"
        ingress_values = {
            "cluster_issuer": self.cluster_issuer,
            "environment_namespace": self.namespace,
            "domain": bad_hostname,
            "service_name": smarter_settings.platform_name,
        }

        # create and apply the ingress manifest
        template_path = os.path.join(HERE, "./data/ingress.yaml.tpl")
        with open(template_path, encoding="utf-8") as ingress_template:
            template = Template(ingress_template.read())
            manifest = template.substitute(ingress_values)
        with self.assertRaises(KubernetesHelperException):
            kubernetes_helper.apply_manifest(manifest)
