# -*- coding: utf-8 -*-
"""A module for interacting with Kubernetes clusters."""

import os
from string import Template

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes import utils as k8s_utils

from .conf import settings as smarter_settings


HERE = os.path.abspath(os.path.dirname(__file__))


def get_kubeconfig() -> str:
    """Generate a kubeconfig file for the EKS cluster."""
    eks_client = smarter_settings.aws_session.client("eks")
    response = eks_client.describe_cluster(name="apps-hosting-service")
    cluster = response["cluster"]

    kubeconfig_values = {
        "ca_data": cluster["certificateAuthority"]["data"],
        "server_endpoint": cluster["endpoint"],
        "cluster_name": smarter_settings.aws_eks_cluster_name,
    }
    kubeconfig_filespec = os.path.join(HERE, "./templates/kubeconfig.tpl")
    with open(kubeconfig_filespec, "r", encoding="utf-8") as kubeconfig_template:
        template = Template(kubeconfig_template.read())
        kubeconfig = template.substitute(kubeconfig_values)

    return kubeconfig


def get_k8s_client() -> k8s_client.ApiClient:
    """
    Returns Kubernetes API client, which is roughly the equivalent
    of a `kubectl` client.
    """
    kubeconfig = get_kubeconfig()
    k8s_config.load_kube_config(kubeconfig)
    return k8s_client.ApiClient()


def apply_manifest(manifest):
    """Apply a Kubernetes manifest to the cluster."""
    k8s_api = get_k8s_client()
    k8s_utils.create_from_yaml(k8s_api, manifest)
