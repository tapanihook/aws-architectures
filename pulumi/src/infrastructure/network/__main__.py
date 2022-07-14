from pulumi import Config
import pulumi
from pulumi_awsx import ec2

from components.virtual_network import VirtualNetworkConfig, VirtualNetwork


k8s_config = Config("k8s_vpc_config")
network_name = "k8s-vpc"


k8s_network_config = VirtualNetworkConfig(
    network_name="k8s-network",
    cidr_block=k8s_config.require("cidr_block"),
    environment=k8s_config.require("environment"),
    tags={"maintainer": k8s_config.require("maintainer")}
)

k8s_network = VirtualNetwork(k8s_network_config)
