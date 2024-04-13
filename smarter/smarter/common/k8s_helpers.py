# -*- coding: utf-8 -*-
"""A module for interacting with Kubernetes clusters."""

import logging
import os
from string import Template

import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes import utils as k8s_utils

from .conf import settings as smarter_settings


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


def get_kubeconfig() -> dict:
    """Generate a kubeconfig file for the EKS cluster."""

    # Retrieve the EKS cluster configuration from AWS
    eks_client = smarter_settings.aws_session.client("eks")
    response = eks_client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)
    logger.info("retrieved AWS EKS cluster configuration for %s", smarter_settings.aws_eks_cluster_name)
    cluster = response["cluster"]

    # format the kubeconfig file using a yaml template
    # the template is a string with placeholders for the cluster's certificate authority data,
    # the server endpoint, and the cluster name.
    kubeconfig_values = {
        "ca_data": cluster["certificateAuthority"]["data"],
        "server_endpoint": cluster["endpoint"],
        "cluster_name": smarter_settings.aws_eks_cluster_name,
    }
    kubeconfig_filespec = os.path.join(HERE, "./templates/kubeconfig.tpl")
    with open(kubeconfig_filespec, "r", encoding="utf-8") as kubeconfig_template:
        template = Template(kubeconfig_template.read())
        kubeconfig = template.substitute(kubeconfig_values)

    # convert the yaml kubeconfig file to a JSON dictionary
    json_obj = yaml.safe_load(kubeconfig)

    return json_obj


def get_k8s_client() -> k8s_client.ApiClient:
    """
    Returns Kubernetes API client, which is roughly the equivalent
    of a `kubectl` client.
    """
    kubeconfig = get_kubeconfig()
    k8s_config.load_kube_config_from_dict(kubeconfig)
    logger.info("loaded Kubernetes configuration")
    return k8s_client.ApiClient()


def apply_manifest(manifest: str):
    """Apply a Kubernetes manifest to the cluster."""
    k8s_api = get_k8s_client()
    logger.info("applying Kubernetes manifest to cluster %s", smarter_settings.aws_eks_cluster_name)
    json_obj = yaml.safe_load(manifest)
    k8s_utils.create_from_dict(k8s_client=k8s_api, data=json_obj)
