'''
Demonstrate how to install External Secrets Operator and integrate
it to the AWS Secrets Manager
'''
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


external_secrets_config = pulumi.Config()
environment = external_secrets_config.require("environment")
k8s_cluster_stack = pulumi.StackReference(
    f"{environment}-k8s-cluster-stack",
    stack_name=external_secrets_config.require("k8s_cluster_stack_name")
)
kubeconfig = k8s_cluster_stack.outputs["k8s_cluster_kubeconfig"]
k8s_provider = pulumi_kubernetes.Provider(
    f"{environment}-k8s-provider", kubeconfig=kubeconfig
)
aws_account_id = pulumi_aws.get_caller_identity().account_id
aws_test_secret_name = "test-secret-1"
my_oidc_url = k8s_cluster_stack.outputs["k8s_cluster_info"]["identities"][0]["oidcs"][0]["issuer"]
assume_role_policy = my_oidc_url.apply(create_assume_role_policy)

service_account_role = pulumi_aws.iam.Role(
    f"{environment}-eso-service-account-role",
    assume_role_policy=assume_role_policy)

secrets_manager_read_policy = pulumi_aws.iam.Policy(
    f"{environment}-eso-service-account-role-secrets-manager-read-policy",
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
                    "Resource": ("arn:aws:secretsmanager:*:*:secret:"
                                 f"{environment}*")
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
    f"{environment}-eso-sa-role-secrets-manager-read-policy-attach",
    policy_arn=secrets_manager_read_policy.arn,
    role=service_account_role
)

service_account_role_arn = service_account_role.id.apply(
    lambda name: f"arn:aws:iam::{aws_account_id}:role/{name}")

eso_service_account_name = "eso-sa"
eso_service_account = pulumi_kubernetes.core.v1.ServiceAccount(
    f"{environment}-eso-service-account",
    api_version="v1",
    kind="ServiceAccount",
    metadata={
        "name": eso_service_account_name,
        "namespace": "default",
        "annotations": {
            "eks.amazonaws.com/role-arn": service_account_role_arn
        }
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider)
)

external_secrets_release = pulumi_kubernetes.helm.v3.Release(
    f"{environment}-external-secrets-release",
    create_namespace=True,
    chart="external-secrets",
    namespace="external-secrets",
    values={"installCRDs": "true"},
    version=external_secrets_config.require("chart_version"),
    repository_opts=pulumi_kubernetes.helm.v3.RepositoryOptsArgs(
        repo=external_secrets_config.require("chart_url")
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider)
)

test_secret = pulumi_aws.secretsmanager.Secret(
    f"{environment}-secret",
    name="eso-secret-1")
pulumi_aws.secretsmanager.SecretVersion(
    f"{environment}-eso-secret-version",
    secret_id=test_secret.arn,
    secret_string=external_secrets_config.require_secret("test-secret-1")
)

secretstore = pulumi_kubernetes.apiextensions.CustomResource(
    f"{environment}-secretstore",
    api_version="external-secrets.io/v1beta1",
    kind="SecretStore",
    metadata={"name": "secretstore-sample"},
    spec={
        "provider": {
            "aws": {
                "service": "SecretsManager",
                "region": "eu-west-1",
                "auth": {
                    "jwt": {
                        "serviceAccountRef": {
                            "name": eso_service_account_name
                        }
                    }
                }
            }
        }
    },
    opts=pulumi.ResourceOptions(depends_on=external_secrets_release)
)

pulumi_kubernetes.apiextensions.CustomResource(
    f"{environment}-externalsecret-sample",
    api_version="external-secrets.io/v1beta1",
    kind="ExternalSecret",
    metadata={"name": "externalsecret-sample"},
    spec={
        "refreshInterval": "1h",
        "secretStoreRef": {
            "name": "secretstore-sample",
            "kind": "SecretStore"
        },
        "target": {"name": "test-k8s-secret"},
        "data": [
            {
                "secretKey": "test-secret-1",
                "remoteRef": {
                   "key": "test-secret-1"
                }
            }
        ]
    },
    opts=pulumi.ResourceOptions(depends_on=secretstore)
)
