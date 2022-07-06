from pulumi import Config
import pulumi
from pulumi_eks import Cluster

base_name = "k8s-cluster"
network_config = Config("network_config")
network_stack = pulumi.StackReference("shared-network", stack_name=network_config.require("k8s_network_stack_name"))
k8s_cluster_vpc_id = network_stack.outputs["vpc_id"]
my_private_subnet_ids = network_stack.outputs["private_subnet_ids"]
pulumi.log.debug(f"Subnet ids: {my_private_subnet_ids}")
pulumi.log.debug(f"VPC id: {k8s_cluster_vpc_id}")


tools_k8s_cluster = Cluster(
    f"{base_name}-control-plane",
    create_oidc_provider=True,
    desired_capacity=2,
    enabled_cluster_log_types=["api", "audit", "authenticator", "controllerManager", "scheduler"],
    encrypt_root_block_device=True,
    # instance_role=
    instance_type="m5.large", # restrict to specific
    name=base_name,
    max_size=3,
    min_size=2,
    # node_ami_id=
    # skip_default_node_group=True,
    node_root_volume_encrypted=True,
    node_root_volume_size=100,
    node_ami_id="ami-0fd784d3523cda0fa",
    private_subnet_ids=my_private_subnet_ids,
    #role_mappings=
    # tags
    version="1.22", # Restrict to supported
    vpc_id=k8s_cluster_vpc_id
)
