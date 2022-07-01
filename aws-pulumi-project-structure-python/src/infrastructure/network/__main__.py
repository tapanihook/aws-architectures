from pulumi import Config
import pulumi
from pulumi_awsx import ec2


k8s_config = Config("k8s_vpc_config")
base_name = "k8s-vpc"
public_subnet_args = ec2.SubnetSpecArgs(
    cidr_mask=24,
    type=ec2.SubnetType.PUBLIC,
    name=f"{base_name}-public-subnet"
)
db_subnet_args = ec2.SubnetSpecArgs(
    cidr_mask=24,
    type=ec2.SubnetType.ISOLATED,
    name=f"{base_name}-db-subnet"
)
nodegroup_public_subnet_args = ec2.SubnetSpecArgs(
    cidr_mask=24,
    type=ec2.SubnetType.PRIVATE,
    name=f"{base_name}-nodegroup-subnet"
)

k8s_vpc = ec2.Vpc(
    f"k8s-vpc-{k8s_config.require('environment')}",
    cidr_block=k8s_config.get("cidr_block"),
    enable_dns_hostnames=True,
    number_of_availability_zones=2,
    subnet_specs=[db_subnet_args, nodegroup_public_subnet_args, public_subnet_args],
    tags={
        "Pulumi": "true",
        "Environment": k8s_config.require("environment"),
        "Name": f"k8s-vpc-{k8s_config.require('environment')}",
        "Pulumi-Stack": pulumi.get_stack()
    }
)

pulumi.export("vpc_id", k8s_vpc.vpc_id)
pulumi.export("private_subnet_ids", k8s_vpc.private_subnet_ids)