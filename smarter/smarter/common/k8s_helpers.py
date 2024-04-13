# -*- coding: utf-8 -*-
"""A module for interacting with Kubernetes clusters."""

import logging
import os
import subprocess

import yaml

from .conf import settings as smarter_settings


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


class Singleton(type):
    """A metaclass for creating singleton classes."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class KubernetesHelper(metaclass=Singleton):
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
        with open(self.kubeconfig_path, "r", encoding="utf-8") as f:
            self._kubeconfig = yaml.safe_load(f)
        return self._kubeconfig

    def update_kubeconfig(self):
        """Generate a fresh kubeconfig file for the EKS cluster."""
        print("update_kubeconfig()")
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
        self.update_kubeconfig()
        logger.info("applying Kubernetes manifest to cluster %s", smarter_settings.aws_eks_cluster_name)
        with subprocess.Popen(
            ["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            _, stderr = process.communicate(input=manifest.encode())
            if process.returncode != 0:
                # pylint: disable=W0719
                raise Exception(f"Failed to apply manifest: {stderr.decode()}")

    def get_namespaces(self):
        """Get all namespaces in the Kubernetes cluster."""
        logger.info("retrieving namespaces from Kubernetes cluster %s", smarter_settings.aws_eks_cluster_name)
        self.update_kubeconfig()
        subprocess.check_call(["kubectl", "get", "pods", "-n", "kube-system"])


kubernetes_helper = KubernetesHelper()
