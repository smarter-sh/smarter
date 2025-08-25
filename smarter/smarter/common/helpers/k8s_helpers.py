"""A module for interacting with Kubernetes clusters."""

# pylint: disable=W0613

import json
import logging
import os
import subprocess
import time
from typing import Tuple

from smarter.common.exceptions import SmarterException
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import get_readonly_yaml_file

from ..classes import Singleton, SmarterHelperMixin
from ..conf import settings as smarter_settings


logger = logging.getLogger(__name__)
module_prefix = "smarter.common.helpers.k8s_helpers"


class KubernetesHelperException(SmarterException):
    """Base class for Kubernetes helper exceptions."""


class KubernetesHelper(SmarterHelperMixin, metaclass=Singleton):
    """A helper class for interacting with Kubernetes clusters."""

    _kubeconfig: dict = None
    _configured: bool = False

    def __init__(self, kubeconfig: dict = None, configured: bool = False, **kwargs):
        super().__init__()
        default_kubeconfig = {"apiVersion": "v1"}
        self._configured = configured
        self._kubeconfig = kubeconfig or default_kubeconfig

    @property
    def configured(self) -> bool:
        return self._configured

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
        if self.configured:
            return

        prefix = formatted_text(f"{module_prefix}.update_kubeconfig()")

        logger.info(
            "%s.update_kubeconfig() updating kubeconfig for Kubernetes cluster %s",
            prefix,
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
        self._configured = True

    def apply_manifest(self, manifest: str):
        """Apply a Kubernetes manifest to the cluster."""
        prefix = formatted_text(f"{module_prefix}.apply_manifest()")

        logger.info(
            "%s applying Kubernetes manifest to cluster %s:\n%s",
            prefix,
            smarter_settings.aws_eks_cluster_name,
            manifest,
        )
        self.update_kubeconfig()
        with subprocess.Popen(
            ["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            _, stderr = process.communicate(input=manifest.encode())
            if process.returncode != 0:
                # pylint: disable=W0719
                raise KubernetesHelperException(f"Failed to apply manifest: {stderr.decode()}")

    def verify_ingress_resources(self, hostname: str, namespace: str) -> Tuple[bool, bool, bool]:
        """
        Verify that an ingress and all child resources exist in the
        cluster.
        """
        prefix = formatted_text(f"{module_prefix}.verify_ingress_resources()")

        logger.info(
            "%s.verify_ingress_resources() verifying ingress resources in cluster %s, hostname %s, namespace %s",
            prefix,
            smarter_settings.aws_eks_cluster_name,
            hostname,
            namespace,
        )

        ingress_name = hostname
        ingress_verified = self.verify_ingress(ingress_name, namespace)

        secret_name = f"{hostname}-tls"
        secret_verified = self.verify_secret(secret_name, namespace)

        certificate_name = secret_name
        max_attempts = 30
        sleep_time = 60
        # attempt to verify the certificate once per minute for up to a half hour.
        for _ in range(max_attempts):
            certificate_verified = self.verify_certificate(certificate_name, namespace)
            if certificate_verified:
                break
            logger.info(
                "%s.verify_ingress_resources() certificate %s %s not ready, sleeping for %s seconds",
                prefix,
                hostname,
                namespace,
                sleep_time,
            )
            time.sleep(sleep_time)
        else:
            logger.error(
                "%s.verify_ingress_resources() certificate not ready after %s attempts",
                prefix,
                max_attempts,
            )

        return ingress_verified, certificate_verified, secret_verified

    def verify_ingress(self, name: str, namespace: str) -> bool:
        """
        Verify that an Ingress resource exists in the cluster.
        command:
        - kubectl get ingress smarter.3141-5926-5359.api.smarter.sh -n smarter-platform-prod -o json
        """
        prefix = formatted_text(f"{module_prefix}.verify_ingress()")
        logger.info(
            "%s verifying ingress in cluster %s, name %s, namespace %s",
            prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        command = ["kubectl", "get", "ingress", name, "-n", namespace, "-o", "json"]
        try:
            self.update_kubeconfig()
            output = subprocess.check_output(command)
            json.loads(output)
            logger.info("%s found ingress resource %s %s", prefix, name, namespace)
        except subprocess.CalledProcessError:
            logger.warning("%s did not find ingress resource %s %s", prefix, name, namespace)
            return False
        except json.JSONDecodeError as e:
            logger.exception("%s failed to parse ingress resource: %s", prefix, e)
            return False
        return True

    def verify_certificate(self, name: str, namespace: str) -> bool:
        """
        Verify that a cert-manager certificate resource exists in the cluster
        and is in a ready state.

        command:
        - kubectl get certificate smarter.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod -o json

        parse json response and check for the following:
        - status.conditions.type == Ready
        """
        prefix = formatted_text(f"{module_prefix}.verify_certificate()")
        logger.info(
            "%s verifying certificate in cluster %s, name %s, namespace %s",
            prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        command = ["kubectl", "get", "certificate", name, "-n", namespace, "-o", "json"]
        # if the certificate is found, the output will be the certificate data in json format.
        try:
            self.update_kubeconfig()
            output = subprocess.check_output(command, text=True)
            logger.info("%s found certificate resource for %s %s", prefix, name, namespace)
            certificate_info: dict = None
            try:
                certificate_info = json.loads(output)
                logger.info("%s parsed json certificate data %s %s", prefix, name, namespace)
            except json.JSONDecodeError as e:
                logger.exception("%s Failed to parse certificate resource: %s", prefix, e)
                return False

            # try to parse the json data and check if the certificate is ready.
            # status.conditions.status == True and status.conditions.type == Ready
            try:
                ready_status = next(
                    (
                        condition["status"]
                        for condition in certificate_info["status"]["conditions"]
                        if condition["type"] == "Ready"
                    ),
                    None,
                )
                certificate_issued = str(ready_status).lower() == "true"
                if certificate_issued:
                    logger.info(
                        "%s Certificate %s in namespace %s is issued and in a ready state.", prefix, name, namespace
                    )
                else:
                    logger.warning(
                        "%s Certificate %s in namespace %s is not ready. Status: %s",
                        prefix,
                        name,
                        namespace,
                        ready_status,
                    )
                    return False
            except KeyError as e:
                logger.exception("%s Could not parse certificate json data for %s %s: %s", prefix, name, namespace, e)
                return False
        except subprocess.CalledProcessError as e:
            logger.warning("%s Failed to retrieve certificate %s %s", prefix, name, namespace)
            return False
        return True

    def verify_secret(self, name: str, namespace: str) -> bool:
        """
        Verify that a secret resource exists in the cluster.
        command:
        - kubectl get secret smarter.3141-5926-5359.api.smarter.sh-tls -n smarter-platform-prod -o json
        """
        prefix = formatted_text(f"{module_prefix}.verify_secret()")
        logger.info(
            "%s verifying secret in cluster %s, name %s, namespace %s",
            prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        command = ["kubectl", "get", "secret", name, "-n", namespace, "-o", "json"]
        # if the secret is found, the output will be the secret data in json format.
        try:
            self.update_kubeconfig()
            output = subprocess.check_output(command)
            json.loads(output)
            logger.info("%s secret %s in namespace %s is ready", prefix, name, namespace)
            return True
        except subprocess.CalledProcessError:
            logger.error("%s Failed to verify secret resource %s %s", prefix, name, namespace)
            return False
        except json.JSONDecodeError as e:
            logger.exception("%s Failed to parse secret resource: %s", prefix, e)
            return False
        return True

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

    def get_namespaces(self) -> dict:
        """Get all namespaces in the Kubernetes cluster."""
        logger.info("retrieving namespaces from Kubernetes cluster %s", smarter_settings.aws_eks_cluster_name)
        self.update_kubeconfig()
        output = subprocess.check_output(["kubectl", "get", "pods", "-n", "kube-system", "-o", "json"])
        output_dict = json.loads(output)
        return output_dict


kubernetes_helper = KubernetesHelper()
