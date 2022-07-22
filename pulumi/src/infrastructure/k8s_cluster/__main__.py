"""
Provision AWS EKS components. This includes
- EKS control plane
- worker nodes configured as managed node group and managed by auto scaling
  group
"""

from pulumi import Config
import pulumi
import pulumi_aws
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

desired_node_capacity = cluster_config.get("desired_node_capacity")
if not desired_node_capacity:
    desired_node_capacity = 2
min_node_capacity = cluster_config.get("min_node_capacity")
environment = network_config.get("environment")
if not environment:
    environment = "test"
maintainer = network_config.get("maintainer")
if not maintainer:
    my_arn = pulumi_aws.get_caller_identity().arn
    maintainer = my_arn.split("/")[-1]
network_name = f"{maintainer}-network"
if not min_node_capacity:
    min_node_capacity = 1
max_node_capacity = cluster_config.get("max_node_capacity")
if not max_node_capacity:
    max_node_capacity = 3
max_node_capacity = cluster_config.get("max_node_capacity")
k8s_version = cluster_config.get("k8s_version")
if not k8s_version:
    k8s_version = "1.22"
# NOTE: Cluster class should default to latest node ami
#       but instead of ami if we get error
node_ami_id = cluster_config.get("node_ami_id")
if not node_ami_id:
    ami_result = pulumi_aws.ec2.get_ami(
        filters=[
            pulumi_aws.ec2.GetAmiFilterArgs(
                name="name", # amazon-eks-node-1.22
                values=[f"amazon-eks-node-{k8s_version}-*"],
            ),
            pulumi_aws.ec2.GetAmiFilterArgs(
                name="architecture",
                values=["x86_64"],
            )
        ],
        most_recent=True,
        owners=["amazon"])
    node_ami_id = ami_result.id

base_name = f"{maintainer}-k8s-cluster-{environment}"
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
    node_ami_id=node_ami_id,
    node_associate_public_ip_address=False,
    private_subnet_ids=my_private_subnet_ids,
    version=k8s_version,
    vpc_id=k8s_cluster_vpc_id
)
pulumi.export("k8s_cluster_info", my_k8s_cluster.eks_cluster)
pulumi.export("k8s_cluster_kubeconfig", my_k8s_cluster.kubeconfig)
