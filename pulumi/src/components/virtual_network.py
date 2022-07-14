import pulumi
from pulumi import ComponentResource, ResourceOptions
from pulumi_awsx import ec2
from pydantic import PositiveInt
from typing import Optional


from lib.base_types import AwsBase


MIN_SUBNETS = PositiveInt(2)
MAX_NET_PREFIX = (
    21  # A CIDR block of prefix length 21 allows for up to 8 /24 subnet blocks
)
SUBNET_PREFIX_V4 = (
    24  # A CIDR block of prefix length 24 allows for up to 255 individual IP addresses
)


class VirtualNetworkConfig(AwsBase):
    """Schema definition for VPC configuration values."""

    network_name: str
    cidr_block: str
    environment: str
    num_subnets: PositiveInt = MIN_SUBNETS


class VirtualNetwork(ComponentResource):
    """Pulumi component for building an AWS VPC."""

    def __init__(self, network_config: VirtualNetworkConfig, opts: Optional[ResourceOptions] = None):
        """Build an AWS VPC with subnets, internet gateway, and routing table.
        :param vpc_config: Configuration object for customizing the created VPC and
            associated resources.
        :type vpc_config: VirtualNetworkConfig
        :param opts: Optional resource options to be merged into the defaults.  Useful
            for handling things like AWS provider overrides.
        :type opts: Optional[ResourceOptions]
        """
        super().__init__("components:virtual_network:VirtualNetwork", f"{network_config.environment}-{network_config.network_name}", None, opts)
        resource_options = ResourceOptions.merge(  # type: ignore
            ResourceOptions(parent=self),
            opts,
        )


        self.network_name = network_config.network_name

        self.public_subnet_args = ec2.SubnetSpecArgs(
            cidr_mask=24,
            type=ec2.SubnetType.PUBLIC,
            name="public-subnet"
        )
        self.db_subnet_args = ec2.SubnetSpecArgs(
            cidr_mask=24,
            type=ec2.SubnetType.ISOLATED,
            name="db-subnet"
        )
        self.nodegroup_public_subnet_args = ec2.SubnetSpecArgs(
            cidr_mask=24,
            type=ec2.SubnetType.PRIVATE,
            name="nodegroup-subnet"
        )

        self.my_vpc = ec2.Vpc(
            f"{network_config.environment}-{network_config.network_name}-vpc",
            cidr_block=network_config.cidr_block,
            enable_dns_hostnames=True,
            number_of_availability_zones=network_config.num_subnets,
            subnet_specs=[self.db_subnet_args, self.nodegroup_public_subnet_args, self.public_subnet_args],
            tags={
                **network_config.tags,
                "environment": network_config.environment,
                "name": f"vpc-{network_config.environment}"
            }
        )

        pulumi.export("vpc_id", self.my_vpc.vpc_id)
        pulumi.export("private_subnet_ids", self.my_vpc.private_subnet_ids)