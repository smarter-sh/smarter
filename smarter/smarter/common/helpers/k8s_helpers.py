"""A module for interacting with Kubernetes clusters."""

import logging
import os
import subprocess
from typing import Tuple

from smarter.lib.unittest.utils import get_readonly_yaml_file

from ..classes import Singleton, SmarterHelperMixin
from ..conf import settings as smarter_settings


logger = logging.getLogger(__name__)


class KubernetesHelper(SmarterHelperMixin, metaclass=Singleton):
    """A helper class for interacting with Kubernetes clusters."""

    _kubeconfig: dict = None

    @property
    def kubeconfig_path(self) -> str:
        return os.path.join(smarter_settings.data_directory, ".kube", "config")

    @property
    def kubeconfig(self) -> dict:
        """Return the kubeconfig file as a dictionary."""
        if self._kubeconfig:
            return self._kubeconfig
        self._kubeconfig = get_readonly_yaml_file(self.kubeconfig_path)
        return self._kubeconfig

    def update_kubeconfig(self):
        """Generate a fresh kubeconfig file for the EKS cluster."""
        logger.info(
            "%s.update_kubeconfig() updating kubeconfig for Kubernetes cluster %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
        )
        command = [
            "aws",
            "eks",
            "update-kubeconfig",
            "--region",
            smarter_settings.aws_region,
            "--name",
            smarter_settings.aws_eks_cluster_name,
        ]
        subprocess.check_call(command)

    def apply_manifest(self, manifest: str):
        """Apply a Kubernetes manifest to the cluster."""
        logger.info(
            "%s.apply_manifest() applying Kubernetes manifest to cluster %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
        )
        self.update_kubeconfig()
        with subprocess.Popen(
            ["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            _, stderr = process.communicate(input=manifest.encode())
            if process.returncode != 0:
                # pylint: disable=W0719
                raise Exception(f"Failed to apply manifest: {stderr.decode()}")

    def delete_ingress_resources(self, hostname: str, namespace: str) -> Tuple[bool, bool, bool]:
        """
        Delete an ingress and all child resources from the cluster.
        commands:
        - kubectl delete ingress education.3141-5926-5359.api.smarter.sh -n smarter-platform-prod
        - kubectl delete certificate education.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod
        - kubectl delete secret education.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod
        """
        logger.info(
            "%s.delete_ingress_resources() deleting ingress resources from cluster %s, hostname %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            hostname,
            namespace,
        )

        ingress_name = hostname
        ingress_deleted = self.delete_ingress(ingress_name, namespace)

        certificate_name = f"{hostname}-tls"
        certificate_deleted = self.delete_certificate(certificate_name, namespace)

        secret_name = certificate_name
        secret_deleted = self.delete_secret(secret_name, namespace)

        return ingress_deleted, certificate_deleted, secret_deleted

    def delete_ingress(self, ingress_name: str, namespace: str) -> bool:
        """
        Delete an Ingress resource from the cluster.
        command:
        - kubectl delete ingress education.3141-5926-5359.api.smarter.sh -n smarter-platform-prod
        """
        logger.info(
            "%s.delete_ingress() deleting ingress from cluster %s, name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            ingress_name,
            namespace,
        )
        self.update_kubeconfig()
        command = ["kubectl", "delete", "ingress", ingress_name, "-n", namespace]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete ingress resource: %s", error)
            return False
        return True

    def delete_certificate(self, certificate_name: str, namespace: str) -> bool:
        """
        Delete a cert-manager certificate resource from the cluster.
        command:
        - kubectl delete certificate education.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod
        """
        logger.info(
            "%s.delete_ingress() deleting certificate from cluster %s, certificate_name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            certificate_name,
            namespace,
        )
        self.update_kubeconfig()
        command = ["kubectl", "delete", "certificate", certificate_name, "-n", namespace]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete certificate resource: %s", error)
            return False
        return True

    def delete_secret(self, secret_name: str, namespace: str) -> bool:
        """
        Delete a secret resource from the cluster.
        commands:
        - kubectl delete secret education.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod
        """
        logger.info(
            "%s.delete_ingress() deleting secret from cluster %s, secret_name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            secret_name,
            namespace,
        )
        self.update_kubeconfig()
        command = ["kubectl", "delete", "secret", secret_name, "-n", namespace]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete secret resource: %s", error)
            return False
        return True

    def get_namespaces(self):
        """Get all namespaces in the Kubernetes cluster."""
        logger.info("retrieving namespaces from Kubernetes cluster %s", smarter_settings.aws_eks_cluster_name)
        self.update_kubeconfig()
        subprocess.check_call(["kubectl", "get", "pods", "-n", "kube-system"])


kubernetes_helper = KubernetesHelper()
