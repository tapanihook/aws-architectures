from os import environ
from pulumi import Config
import pulumi
from pulumi_aws import get_caller_identity
from pulumi_awsx import ec2

from components.virtual_network import VirtualNetworkConfig, VirtualNetwork


network_config = Config("network_config")
cidr_block = network_config.get("cidr_block")
if not cidr_block:
    cidr_block = "10.12.0.0/16"
environment = network_config.get("environment")
if not environment:
    environment = "test"
maintainer = network_config.get("maintainer")
if not maintainer:
    my_arn = get_caller_identity().arn
    maintainer = my_arn.split("/")[-1]
network_name = f"{maintainer}-network"

k8s_network_config = VirtualNetworkConfig(
    network_name=network_name,
    cidr_block=cidr_block,
    environment=environment,
    tags={"maintainer": maintainer}
)

k8s_network = VirtualNetwork(k8s_network_config)
