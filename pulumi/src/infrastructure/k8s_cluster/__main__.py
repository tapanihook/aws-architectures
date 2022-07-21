"""
Provision AWS EKS components. This includes
- EKS control plane
- worker nodes configured as managed node group and managed by auto scaling
  group
"""

from pulumi import Config
import pulumi
from pulumi_eks import Cluster


network_config = Config("network_config")
network_stack = pulumi.StackReference(
    "shared-network",
    stack_name=network_config.require("k8s_network_stack_name"))
k8s_cluster_vpc_id = network_stack.outputs["vpc_id"]
my_private_subnet_ids = network_stack.outputs["private_subnet_ids"]
pulumi.log.debug(f"Subnet ids: {my_private_subnet_ids}")
pulumi.log.debug(f"VPC id: {k8s_cluster_vpc_id}")

cluster_config = Config("cluster_config")
base_name = f"{cluster_config.require('environment')}-k8s-cluster"
desired_node_capacity = cluster_config.get("desired_node_capacity")
if not desired_node_capacity:
    desired_node_capacity = 2
min_node_capacity = cluster_config.get("min_node_capacity")
if not min_node_capacity:
    min_node_capacity = 1
max_node_capacity = cluster_config.get("max_node_capacity")
if not max_node_capacity:
    max_node_capacity = 3

# TODO: Add tags
my_k8s_cluster = Cluster(
    base_name,
    create_oidc_provider=True,
    desired_capacity=desired_node_capacity,
    enabled_cluster_log_types=[
        "api", "audit", "authenticator", "controllerManager", "scheduler"],
    encrypt_root_block_device=True,
    instance_type="t3.large",
    name=base_name,
    max_size=max_node_capacity,
    min_size=min_node_capacity,
    node_root_volume_encrypted=True,
    node_root_volume_size=100,
    node_ami_id=cluster_config.require("node_ami_id"),
    node_associate_public_ip_address=False,
    private_subnet_ids=my_private_subnet_ids,
    version=cluster_config.require("k8s_version"),
    vpc_id=k8s_cluster_vpc_id
)
pulumi.export("k8s_cluster_info", my_k8s_cluster.eks_cluster)
pulumi.export("k8s_cluster_kubeconfig", my_k8s_cluster.kubeconfig)
