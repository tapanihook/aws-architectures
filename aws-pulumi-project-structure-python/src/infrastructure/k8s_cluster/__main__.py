from pulumi import Config
import pulumi
from pulumi_eks import Cluster


cluster_config = Config("cluster_config")
network_config = Config("network_config")
network_stack = pulumi.StackReference("shared-network", stack_name=network_config.require("k8s_network_stack_name"))
k8s_cluster_vpc_id = network_stack.outputs["vpc_id"]
my_private_subnet_ids = network_stack.outputs["private_subnet_ids"]
pulumi.log.debug(f"Subnet ids: {my_private_subnet_ids}")
pulumi.log.debug(f"VPC id: {k8s_cluster_vpc_id}")
base_name = f"{cluster_config.require('environment')}-k8s-cluster"

tools_k8s_cluster = Cluster(
    base_name,
    create_oidc_provider=True,
    desired_capacity=2,
    enabled_cluster_log_types=["api", "audit", "authenticator", "controllerManager", "scheduler"],
    encrypt_root_block_device=True,
    instance_type="m5.large", # restrict to specific
    name=base_name,
    max_size=3,
    min_size=2,
    node_root_volume_encrypted=True,
    node_root_volume_size=100,
    node_ami_id=cluster_config.require("node_ami_id"),
    private_subnet_ids=my_private_subnet_ids,
    #role_mappings=
    # tags
    version=cluster_config.require("k8s_version"),
    vpc_id=k8s_cluster_vpc_id
)
