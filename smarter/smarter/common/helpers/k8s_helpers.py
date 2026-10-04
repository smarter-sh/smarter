"""A module for interacting with Kubernetes clusters."""

# pylint: disable=W0613

import os
import subprocess
import time
from typing import Optional, Tuple, Union

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterException
from smarter.common.helpers.aws_helpers import aws_helper
from smarter.common.mixins import Singleton, SmarterHelperMixin
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging

logger = logging.getLogger(__name__)
module_prefix = logging.formatted_text(f"{__name__}.KubernetesHelper")


class KubernetesHelperException(SmarterException):
    """Base class for Kubernetes helper exceptions."""


class KubernetesHelper(SmarterHelperMixin, metaclass=Singleton):
    """
    Helper class for interacting with Kubernetes clusters.

    This class provides a set of utility methods to manage and verify Kubernetes resources
    such as Ingresses, Certificates, and Secrets, as well as to apply manifests and update
    kubeconfig files for EKS clusters. It is designed to be used as a singleton and integrates
    with AWS EKS and cert-manager.

    Attributes
    ----------
    _kubeconfig : dict
        The loaded kubeconfig as a dictionary.
    _configured : bool
        Indicates whether the kubeconfig has been configured.

    Parameters
    ----------
    kubeconfig : dict, optional
        The kubeconfig dictionary to use. If not provided, a default is used.
    configured : bool, optional
        Whether the helper is already configured.
    """

    _kubeconfig: Optional[dict] = None
    _configured: bool = False
    _namespace_verified: bool = False

    def __init__(self, kubeconfig: Optional[dict] = None, configured: bool = False, **kwargs):
        super().__init__()
        default_kubeconfig = {"apiVersion": "v1"}
        self._configured = configured
        self._kubeconfig = kubeconfig or default_kubeconfig
        logger.debug(
            "%s initialized with kubeconfig: %s, configured: %s",
            module_prefix,
            self._kubeconfig,
            self._configured,
        )
        if self.ready:
            msg = f"{module_prefix}.ready() - {self.formatted_state_ready}."
            logger.info(msg)
        else:
            msg = f"{module_prefix}.ready() - {self.formatted_state_not_ready}"
            logger.error(msg)

    @property
    def ready(self) -> bool:
        """
        Return whether the Kubernetes helper is ready for use.

        Returns True
        if Kubernetes is configured, AND, the Kubernetes namespace exists.

        :return: True if ready, False otherwise.
        :rtype: bool

        smarter_settings.environment_namespace
        """
        if not aws_helper.ready:
            msg = (
                f"{module_prefix}.ready() {self.formatted_text_red('AWS not ready, cannot configure KubernetesHelper')}"
            )
            logger.warning(msg)
            return False

        if not self.configured:
            msg = f"{module_prefix}.ready() {self.formatted_text_red('KubernetesHelper not configured')}"
            logger.warning(msg)
            return False

        if not self.namespace_verified:
            msg = f"{module_prefix}.ready() {self.formatted_text_red(f'KubernetesHelper namespace {smarter_settings.environment_namespace} does not exist')}"
            logger.warning(msg)
            return False

        is_ready = self.configured and self.namespace_verified

        if is_ready:
            return True
        return False

    @property
    def namespace_verified(self) -> bool:
        """
        Return whether the Kubernetes namespace has been verified.

        :return: True if the namespace has been verified, False otherwise.
        :rtype: bool
        """
        if self._namespace_verified:
            return True

        self._namespace_verified = self.verify_namespace(smarter_settings.environment_namespace)

        return self._namespace_verified

    @property
    def configured(self) -> bool:
        """
        Return whether the kubeconfig has been configured.

        :return: True if configured, False otherwise.
        :rtype: bool
        """
        if self._configured:
            return True

        self._configured = self.update_kubeconfig()

        return self._configured

    @property
    def kubeconfig_path(self) -> str:
        """
        Return the path to the kubeconfig file.

        :return: The kubeconfig file path.
        :rtype: str
        """
        return os.path.join(smarter_settings.data_directory, ".kube", "config")

    @property
    def kubeconfig(self) -> dict:
        """
        Return the kubeconfig file as a dictionary.

        :return: The kubeconfig dictionary.
        :rtype: dict
        """
        if self._kubeconfig:
            return self._kubeconfig
        self._kubeconfig = get_readonly_yaml_file(self.kubeconfig_path)
        logger.debug("%s loaded kubeconfig from path %s", module_prefix, self.kubeconfig_path)
        return self._kubeconfig

    def update_kubeconfig(self) -> bool:
        """
        Generate a fresh kubeconfig file for the EKS cluster.

        This method uses the AWS CLI to update the kubeconfig file for the specified EKS cluster.

        :raises KubernetesHelperException: If the kubeconfig update fails.

        :return: True if the kubeconfig was updated successfully, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.update_kubeconfig() updating kubeconfig for Kubernetes cluster %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
        )
        if not smarter_settings.aws_eks_cluster_name:
            msg = f"{module_prefix}.update_kubeconfig() smarter_settings.aws_eks_cluster_name is not set. Cannot update kubeconfig."
            logger.error(msg)
            return False
        if not smarter_settings.aws_region:
            msg = (
                f"{module_prefix}.update_kubeconfig() smarter_settings.aws_region is not set. Cannot update kubeconfig."
            )
            logger.error(msg)
            return False

        command = [
            "aws",
            "eks",
            "update-kubeconfig",
            "--region",
            smarter_settings.aws_region,
            "--name",
            smarter_settings.aws_eks_cluster_name,
        ]
        try:
            subprocess.check_call(command)
            self._configured = True
            logger.debug("%s.update_kubeconfig() kubeconfig updated successfully", module_prefix)
            return True
        except subprocess.CalledProcessError as e:
            self._configured = False
            msg = f"{module_prefix}.update_kubeconfig() {self.formatted_text_red('Failed to update kubeconfig')}: {e}"
            logger.error(msg)
            return False
        # pylint: disable=broad-except
        except Exception as e:
            self._configured = False
            msg = f"{module_prefix}.update_kubeconfig() {self.formatted_text_red('Unexpected error while updating kubeconfig')}: {e}"
            logger.exception(msg)
            return False

    def apply_manifest(self, manifest: str):
        """
        Apply a Kubernetes manifest to the cluster.

        :param manifest: The Kubernetes manifest as a string.
        :type manifest: str
        :raises KubernetesHelperException: If applying the manifest fails.
        :return: None
        :rtype: None
        """

        logger.info(
            "%s.apply_manifest() applying Kubernetes manifest to cluster %s:\n%s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            manifest,
        )
        if not self.ready:
            return None

        with subprocess.Popen(
            ["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            _, stderr = process.communicate(input=manifest.encode())
            if process.returncode != 0:
                msg = f"{module_prefix}.apply_manifest() {self.formatted_text_red('Failed to apply manifest')}: {stderr.decode()}"
                logger.error(msg)
                raise KubernetesHelperException(f"Failed to apply manifest: {stderr.decode()}")

    def verify_namespace(self, namespace: str) -> bool:
        """
        Verify that a namespace exists in the cluster.

        :param namespace: The name of the namespace.
        :type namespace: str
        :return: True if the namespace exists, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.verify_namespace() verifying namespace in cluster %s, name %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            namespace,
        )
        if not self.configured:
            return False
        command = ["kubectl", "get", "namespace", namespace, "-o", "json"]
        try:
            output = subprocess.check_output(command)
            json.loads(output)
            logger.debug("%s found namespace resource %s", module_prefix, namespace)
        except subprocess.CalledProcessError:
            logger.warning("%s did not find namespace resource %s", module_prefix, namespace)
            return False
        except json.JSONDecodeError as e:
            logger.exception(
                "%s failed to parse namespace resource: %s", module_prefix, self.formatted_text_red(str(e))
            )
            return False
        return True

    def verify_ingress_resources(
        self, hostname: str, namespace: str, max_attempts: int = 30
    ) -> Tuple[bool, bool, bool]:
        """
        Verify that an ingress and all child resources exist in the.

        cluster.

        commands:
        - kubectl get ingress education.3141-5926-5359.api.example.com -n smarter-platform-prod -o json
        - kubectl get certificate education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod -o json
        - kubectl get secret education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod -o json

        :param hostname: The hostname of the ingress.
        :type hostname: str
        :param namespace: The namespace of the ingress.
        :type namespace: str
        :param max_attempts: How many times to check the certificate, a minute apart. A Celery task
            passes 1, and checks again later, so that it does not block its worker while it waits.
        :type max_attempts: int
        :return: A tuple of booleans indicating whether the ingress, certificate, and secret were verified.
        :rtype: Tuple[bool, bool, bool]
        """
        logger.debug(
            "%s.verify_ingress_resources() verifying ingress resources in cluster %s, hostname %s, namespace %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            hostname,
            namespace,
        )

        ingress_name = hostname
        ingress_verified = self.verify_ingress(ingress_name, namespace)

        secret_name = f"{hostname}-tls"
        secret_verified = self.verify_secret(secret_name, namespace)

        certificate_name = secret_name
        sleep_time = 60
        certificate_verified = False
        # attempt to verify the certificate once per minute, by default for up to a half hour.
        for attempt in range(max(1, max_attempts)):
            certificate_verified = self.verify_certificate(certificate_name, namespace)
            if certificate_verified:
                break
            if attempt + 1 >= max_attempts:
                # no sleep after the last attempt.
                logger.error(
                    "%s.verify_ingress_resources() certificate not ready after %s attempts",
                    module_prefix,
                    max_attempts,
                )
                break
            logger.debug(
                "%s.verify_ingress_resources() certificate %s %s not ready, sleeping for %s seconds",
                module_prefix,
                hostname,
                namespace,
                sleep_time,
            )
            time.sleep(sleep_time)

        return ingress_verified, certificate_verified, secret_verified

    def verify_ingress(self, name: str, namespace: str) -> bool:
        """
        Verify that an Ingress resource exists in the cluster.

        commands:
        - kubectl get ingress smarter.3141-5926-5359.api.example.com -n smarter-platform-prod -o json

        :param name: The name of the ingress.
        :type name: str
        :param namespace: The namespace of the ingress.
        :type namespace: str
        :return: True if the ingress exists, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s verifying ingress in cluster %s, name %s, namespace %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        if not self.ready:
            return False
        command = ["kubectl", "get", "ingress", name, "-n", namespace, "-o", "json"]
        try:
            output = subprocess.check_output(command)
            json.loads(output)
            logger.debug("%s found ingress resource %s %s", module_prefix, name, namespace)
        except subprocess.CalledProcessError:
            logger.warning("%s did not find ingress resource %s %s", module_prefix, name, namespace)
            return False
        except json.JSONDecodeError as e:
            logger.exception("%s failed to parse ingress resource: %s", module_prefix, self.formatted_text_red(str(e)))
            return False
        return True

    def verify_certificate(self, name: str, namespace: str) -> bool:
        """
        Verify that a cert-manager certificate resource exists in the cluster.

        and is in a ready state.

        command:
        - kubectl get certificate smarter.3141-5926-5359.api.example.com-tls -n smarter-platform-prod -o json

        parse json response and check for the following:
        - status.conditions.type == Ready

        :param name: The name of the certificate.
        :type name: str
        :param namespace: The namespace of the certificate.
        :type namespace: str
        :return: True if the certificate exists and is ready, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s verifying certificate in cluster %s, name %s, namespace %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        if not self.ready:
            return False
        command = ["kubectl", "get", "certificate", name, "-n", namespace, "-o", "json"]
        # if the certificate is found, the output will be the certificate data in json format.
        try:
            output = subprocess.check_output(command, text=True)
            logger.debug("%s found certificate resource for %s %s", module_prefix, name, namespace)
            certificate_info: dict
            try:
                certificate_info = json.loads(output)
                logger.debug("%s parsed json certificate data %s %s", module_prefix, name, namespace)
            except json.JSONDecodeError as e:
                logger.exception(
                    "%s Failed to parse certificate resource: %s", module_prefix, self.formatted_text_red(str(e))
                )
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
                        "%s Certificate %s in namespace %s is issued and %s.",
                        module_prefix,
                        name,
                        namespace,
                        self.formatted_state_ready,
                    )
                else:
                    logger.warning(
                        "%s Certificate %s in namespace %s is not %s. Status: %s",
                        module_prefix,
                        name,
                        namespace,
                        self.formatted_state_not_ready,
                        ready_status,
                    )
                    return False
            except KeyError as e:
                logger.exception(
                    "%s Could not parse certificate json data for %s %s: %s",
                    module_prefix,
                    name,
                    namespace,
                    self.formatted_text_red(str(e)),
                )
                return False
        except subprocess.CalledProcessError as e:
            logger.warning("%s Failed to retrieve certificate %s %s", module_prefix, name, namespace)
            return False
        return True

    def verify_secret(self, name: str, namespace: str) -> bool:
        """
        Verify that a secret resource exists in the cluster.

        command:
        - kubectl get secret smarter.3141-5926-5359.api.example.com-tls -n smarter-platform-prod -o json

        :param name: The name of the secret.
        :type name: str
        :param namespace: The namespace of the secret.
        :type namespace: str
        :return: True if the secret exists, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s verifying secret in cluster %s, name %s, namespace %s",
            module_prefix,
            smarter_settings.aws_eks_cluster_name,
            name,
            namespace,
        )
        if not self.ready:
            return False
        command = ["kubectl", "get", "secret", name, "-n", namespace, "-o", "json"]
        # if the secret is found, the output will be the secret data in json format.
        try:
            output = subprocess.check_output(command)
            json.loads(output)
            logger.debug(
                "%s secret %s in namespace %s is %s", module_prefix, name, namespace, self.formatted_state_ready
            )
            return True
        except subprocess.CalledProcessError:
            logger.error("%s Failed to verify secret resource %s %s", module_prefix, name, namespace)
            return False
        except json.JSONDecodeError as e:
            logger.exception("%s Failed to parse secret resource: %s", module_prefix, self.formatted_text_red(str(e)))
            return False
        return True

    def delete_ingress_resources(self, hostname: str, namespace: str) -> Tuple[bool, bool, bool]:
        """
        Delete an ingress and all child resources from the cluster.

        commands:
        - kubectl delete ingress education.3141-5926-5359.api.example.com -n smarter-platform-prod --ignore-not-found
        - kubectl delete certificate education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod --ignore-not-found
        - kubectl delete secret education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod --ignore-not-found

        :param hostname: The hostname of the ingress.
        :type hostname: str
        :param namespace: The namespace of the ingress.
        :type namespace: str
        :return: A tuple of booleans indicating whether the ingress, certificate, and secret were deleted.
        :rtype: Tuple[bool, bool, bool]
        """
        logger.debug(
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
        - kubectl delete ingress education.3141-5926-5359.api.example.com -n smarter-platform-prod --ignore-not-found

        :param ingress_name: The name of the ingress.
        :type ingress_name: str
        :param namespace: The namespace of the ingress.
        :type namespace: str
        :return: True if the ingress was deleted, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.delete_ingress() deleting ingress from cluster %s, name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            ingress_name,
            namespace,
        )
        if not self.ready:
            return False
        # --ignore-not-found: a resource that is already gone counts as deleted.
        command = ["kubectl", "delete", "ingress", ingress_name, "-n", namespace, "--ignore-not-found"]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete ingress resource: %s", error)
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception("Unexpected error while deleting ingress resource: %s", e)
            return False
        return True

    def delete_certificate(self, certificate_name: str, namespace: str) -> bool:
        """
        Delete a cert-manager certificate resource from the cluster.

        command:
        - kubectl delete certificate education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod --ignore-not-found

        :param certificate_name: The name of the certificate.
        :type certificate_name: str
        :param namespace: The namespace of the certificate.
        :type namespace: str
        :return: True if the certificate was deleted, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.delete_ingress() deleting certificate from cluster %s, certificate_name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            certificate_name,
            namespace,
        )
        if not self.ready:
            return False
        # --ignore-not-found: a resource that is already gone counts as deleted.
        command = ["kubectl", "delete", "certificate", certificate_name, "-n", namespace, "--ignore-not-found"]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete certificate resource: %s", error)
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception("Unexpected error while deleting certificate resource: %s", e)
            return False
        return True

    def delete_secret(self, secret_name: str, namespace: str) -> bool:
        """
        Delete a secret resource from the cluster.

        commands:
        - kubectl delete secret education.3141-5926-5359.api.example.com-tls -n smarter-platform-prod --ignore-not-found

        :param secret_name: The name of the secret.
        :type secret_name: str
        :param namespace: The namespace of the secret.
        :type namespace: str
        :return: True if the secret was deleted, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.delete_ingress() deleting secret from cluster %s, secret_name %s, namespace %s",
            self.formatted_class_name,
            smarter_settings.aws_eks_cluster_name,
            secret_name,
            namespace,
        )
        if not self.ready:
            return False
        # --ignore-not-found: a resource that is already gone counts as deleted.
        command = ["kubectl", "delete", "secret", secret_name, "-n", namespace, "--ignore-not-found"]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to delete secret resource: %s", error)
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception("Unexpected error while deleting secret resource: %s", e)
            return False
        return True

    def get_resource(self, kind: str, name: str, namespace: str) -> Optional[dict]:
        """
        Get a resource from the cluster.

        command:
        - kubectl get deployment llmhost-1-example -n smarter-platform-prod -o json

        :param kind: The resource kind, e.g. deployment.
        :type kind: str
        :param name: The name of the resource.
        :type name: str
        :param namespace: The namespace of the resource.
        :type namespace: str
        :return: The resource, or None if it does not exist or the cluster is unavailable.
        :rtype: Optional[dict]
        """
        if not self.ready:
            return None
        command = ["kubectl", "get", kind, name, "-n", namespace, "-o", "json", "--ignore-not-found"]
        try:
            output = subprocess.check_output(command, text=True)
        except subprocess.CalledProcessError as e:
            logger.warning("%s.get_resource() failed to get %s %s %s: %s", module_prefix, kind, name, namespace, e)
            return None
        if not output.strip():
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            logger.error("%s.get_resource() failed to parse %s %s: %s", module_prefix, kind, name, e)
            return None

    def list_resources(self, kind: str, namespace: str, selector: Optional[str] = None) -> list[dict]:
        """
        List resources in the cluster, optionally filtered by a label selector.

        command:
        - kubectl get pods -n smarter-platform-prod -l smarter.sh/llmhost=llmhost-1-example -o json

        :param kind: The resource kind, e.g. pods.
        :type kind: str
        :param namespace: The namespace of the resources.
        :type namespace: str
        :param selector: A label selector, e.g. app=example.
        :type selector: Optional[str]
        :return: The resources, or an empty list if there are none or the cluster is unavailable.
        :rtype: list[dict]
        """
        if not self.ready:
            return []
        command = ["kubectl", "get", kind, "-n", namespace, "-o", "json"]
        if selector:
            command += ["-l", selector]
        try:
            output = subprocess.check_output(command, text=True)
            return json.loads(output).get("items", [])
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.warning(
                "%s.list_resources() failed to list %s %s %s: %s", module_prefix, kind, namespace, selector, e
            )
            return []

    def delete_resources(self, kinds: list[str], namespace: str, selector: str) -> bool:
        """
        Delete the resources of several kinds that match a label selector.

        Resources that do not exist are ignored, so that deletion is idempotent.

        command:
        - kubectl delete deployment,service,ingress -n smarter-platform-prod -l smarter.sh/llmhost=llmhost-1-example --ignore-not-found

        :param kinds: The resource kinds, e.g. ["deployment", "service"].
        :type kinds: list[str]
        :param namespace: The namespace of the resources.
        :type namespace: str
        :param selector: A label selector. Required, so that a namespace is never emptied by mistake.
        :type selector: str
        :return: True if the resources were deleted, False otherwise.
        :rtype: bool
        """
        if not kinds or not selector:
            raise KubernetesHelperException("delete_resources() requires kinds and a label selector.")
        if not self.ready:
            return False
        command = ["kubectl", "delete", ",".join(kinds), "-n", namespace, "-l", selector, "--ignore-not-found"]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as e:
            logger.error("%s.delete_resources() failed to delete %s %s: %s", module_prefix, kinds, selector, e)
            return False
        return True

    def get_pod_logs(
        self, namespace: str, selector: str, container: Optional[str] = None, tail: int = 200
    ) -> Optional[str]:
        """
        Get the most recent log lines of the pods that match a label selector.

        command:
        - kubectl logs -n smarter-platform-prod -l smarter.sh/llmhost=llmhost-1-example --tail 200 --prefix

        :param namespace: The namespace of the pods.
        :type namespace: str
        :param selector: A label selector.
        :type selector: str
        :param container: The container, if the pods have several.
        :type container: Optional[str]
        :param tail: The number of lines, per pod.
        :type tail: int
        :return: The log lines, or None if the cluster is unavailable.
        :rtype: Optional[str]
        """
        if not self.ready:
            return None
        command = ["kubectl", "logs", "-n", namespace, "-l", selector, "--tail", str(tail), "--prefix"]
        if container:
            command += ["-c", container]
        try:
            return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.warning("%s.get_pod_logs() failed for %s %s: %s", module_prefix, selector, namespace, e)
            return e.output if isinstance(e.output, str) else None

    def get_namespaces(self) -> Union[dict, None]:
        """
        Get all namespaces in the Kubernetes cluster.

        :return: A dictionary of namespaces.
        :rtype: dict
        """
        logger.debug("retrieving namespaces from Kubernetes cluster %s", smarter_settings.aws_eks_cluster_name)
        if not self.ready:
            return None
        output = subprocess.check_output(["kubectl", "get", "pods", "-n", "kube-system", "-o", "json"])
        output_dict = json.loads(output)
        return output_dict


kubernetes_helper = KubernetesHelper()
