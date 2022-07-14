import json

import pulumi
import pulumi_aws
import pulumi_kubernetes


def create_assume_role_policy(oidc_url):
    oidc_issuer = oidc_url.replace("https://", "")
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": (
                            "arn:aws:iam::"
                            + pulumi_aws.get_caller_identity().account_id
                            + ":oidc-provider/" + oidc_issuer),
                    },
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    "Condition": {
                        "StringLike": {
                            oidc_issuer + ":sub":
                                "system:serviceaccount:*:*"
                            }
                    }
                }
            ]
            }
    )


secret_store_config = pulumi.Config()
environment = secret_store_config.require("environment")
k8s_cluster_stack = pulumi.StackReference(
    f"{environment}-k8s-cluster-stack",
    stack_name=secret_store_config.require("k8s_cluster_stack_name")
)
kubeconfig = k8s_cluster_stack.outputs["k8s_cluster_kubeconfig"]
k8s_provider = pulumi_kubernetes.Provider(
    f"{environment}-k8s-provider", kubeconfig=kubeconfig
)
aws_account_id = pulumi_aws.get_caller_identity().account_id
aws_test_secret_name = "test-secret-1"

oidc_url = k8s_cluster_stack.outputs["k8s_cluster_info"]["identities"][0]["oidcs"][0]["issuer"]

assume_role_policy = oidc_url.apply(create_assume_role_policy)

service_account_role = pulumi_aws.iam.Role(
    f"{environment}-service-account-role",
    assume_role_policy=assume_role_policy)

csi_secrets_store_driver = pulumi_kubernetes.helm.v3.Release(
    f"{environment}-csi-secrets-store",
    chart="secrets-store-csi-driver",
    namespace="kube-system",
    values={
        "syncSecret": {
            "enabled": "true"
        }
    },
    repository_opts=pulumi_kubernetes.helm.v3.RepositoryOptsArgs(
        repo="https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider)
)

csi_secrets_store_provider = pulumi_kubernetes.yaml.ConfigFile(
    f"{environment}-csi-secrets-store-provider-aws",
    file="https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml",
    opts=pulumi.ResourceOptions(
        depends_on=[csi_secrets_store_driver],
        provider=k8s_provider
    )
)

secrets_manager_read_policy = pulumi_aws.iam.Policy(
    f"{environment}-service-account-role-secrets-manager-read-policy",
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetResourcePolicy",
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                        "secretsmanager:ListSecretVersionIds"
                    ],
                    "Resource": f"arn:aws:secretsmanager:*:*:secret:{environment}*"
                },
                {
                    "Effect": "Allow",
                    "Action": "secretsmanager:ListSecrets",
                    "Resource": "*"
                }
            ]
        }
    )
)

secrets_manager_read_policy_attachment = pulumi_aws.iam.RolePolicyAttachment(
    f"{environment}-service-account-role-secrets-manager-read-policy-attach",
    policy_arn=secrets_manager_read_policy.arn,
    role=service_account_role
)

# Create and mount a secret in a demo pod
service_account_role_arn = service_account_role.id.apply(
    lambda name: f"arn:aws:iam::{aws_account_id}:role/{name}")

pulumi_kubernetes.core.v1.ServiceAccount(
    f"{environment}-secret-store-demo-service-account",
    api_version="v1",
    kind="ServiceAccount",
    metadata={
        "name": "app-sa",
        "namespace": "default",
        "annotations": {
            "eks.amazonaws.com/role-arn": service_account_role_arn
        }
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider)
)

test_secret = pulumi_aws.secretsmanager.Secret(
    f"{environment}-secret",
    name="test-secret-1")
pulumi_aws.secretsmanager.SecretVersion(
    f"{environment}-secret-version",
    secret_id=test_secret.arn,
    secret_string=secret_store_config.require_secret("test-secret-1")
)

secret_provider_class = pulumi_kubernetes.yaml.ConfigFile(
    f"{environment}-secret-store-demo-secretproviderclass",
    # TODO: Read from yaml
    file="https://raw.githubusercontent.com/tapanihook/aws-samples/main/aws-pulumi-project-structure-python/src/infrastructure/secret_store_demo/manifests/secretproviderclass.yaml",
    opts=pulumi.ResourceOptions(
        provider=k8s_provider
    )
)

pulumi_kubernetes.yaml.ConfigFile(
    f"{environment}-secret-store-demo-deployment",
    # TODO: Read from yaml
    file="https://raw.githubusercontent.com/tapanihook/aws-samples/main/aws-pulumi-project-structure-python/src/infrastructure/secret_store_demo/manifests/deployment.yaml",
    opts=pulumi.ResourceOptions(
        provider=k8s_provider
    )
)
